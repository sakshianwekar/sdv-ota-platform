/*
 * version_store.c
 *
 * Implementation of version_store.h.
 *
 * Deliberately uses no external JSON library — the schema is fixed and
 * small enough that hand-rolled parsing is safer than adding a dependency
 * that needs to compile on Mac / Windows / Linux identically.
 *
 * Parsing strategy: find each key with strstr(), then extract the value
 * with sscanf(). This is robust for our fixed schema. It is NOT a
 * general-purpose JSON parser and should not be used for anything else.
 */

#include "version_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

/* -------------------------------------------------------------------------
 * Platform helpers
 * ---------------------------------------------------------------------- */

/* Atomic rename is POSIX; on Windows use MoveFileExA with REPLACE flag.
 * We abstract it here so the rest of the code stays clean. */
#ifdef _WIN32
  #include <windows.h>
  static int portable_rename(const char *src, const char *dst) {
      /* MOVEFILE_REPLACE_EXISTING makes this atomic on NTFS */
      return MoveFileExA(src, dst, MOVEFILE_REPLACE_EXISTING) ? 0 : -1;
  }
#else
  static int portable_rename(const char *src, const char *dst) {
      return rename(src, dst);   /* POSIX rename is atomic on same filesystem */
  }
#endif

/* -------------------------------------------------------------------------
 * Internal helpers
 * ---------------------------------------------------------------------- */

/*
 * extract_string_value()
 *
 * Finds  "key": "value"  in [buf] and copies [value] into [out] (max [out_len]).
 * Returns 1 on success, 0 if key not found or value not a quoted string.
 */
static int extract_string_value(const char *buf,
                                 const char *key,
                                 char       *out,
                                 size_t      out_len)
{
    /* Build the search pattern: "key": " */
    char pattern[64];
    snprintf(pattern, sizeof(pattern), "\"%s\":", key);

    const char *pos = strstr(buf, pattern);
    if (!pos) return 0;

    /* Advance past the key + colon, skip whitespace */
    pos += strlen(pattern);
    while (*pos == ' ' || *pos == '\t' || *pos == '\r' || *pos == '\n') pos++;

    if (*pos != '"') return 0;   /* Value must be a quoted string */
    pos++;                        /* Skip opening quote */

    size_t i = 0;
    while (*pos && *pos != '"' && i < out_len - 1) {
        out[i++] = *pos++;
    }
    out[i] = '\0';
    return (*pos == '"') ? 1 : 0;
}

/*
 * extract_null_or_string()
 *
 * Like extract_string_value() but also accepts JSON null.
 * Writes "" into [out] if the value is null.
 * Returns 1 on success, 0 if key not found.
 */
static int extract_null_or_string(const char *buf,
                                   const char *key,
                                   char       *out,
                                   size_t      out_len)
{
    char pattern[64];
    snprintf(pattern, sizeof(pattern), "\"%s\":", key);

    const char *pos = strstr(buf, pattern);
    if (!pos) return 0;

    pos += strlen(pattern);
    while (*pos == ' ' || *pos == '\t' || *pos == '\r' || *pos == '\n') pos++;

    /* null → empty string */
    if (strncmp(pos, "null", 4) == 0) {
        out[0] = '\0';
        return 1;
    }

    /* Otherwise parse as a quoted string */
    return extract_string_value(buf, key, out, out_len);
}

/* -------------------------------------------------------------------------
 * Public API
 * ---------------------------------------------------------------------- */

int vs_read(const char *path, VersionInfo *out)
{
    if (!path || !out) return VS_ERR_INVALID;

    FILE *fp = fopen(path, "r");
    if (!fp) return VS_ERR_FILE;

    /* Read entire file into a buffer. version.json is tiny (<256 bytes). */
    char buf[1024];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    fclose(fp);
    buf[n] = '\0';

    /* Parse each field */
    if (!extract_string_value(buf, "current_version",
                               out->current_version,
                               sizeof(out->current_version))) {
        return VS_ERR_PARSE;
    }

    if (!extract_string_value(buf, "active_slot",
                               out->active_slot,
                               sizeof(out->active_slot))) {
        return VS_ERR_PARSE;
    }

    /* pending_slot is allowed to be null */
    if (!extract_null_or_string(buf, "pending_slot",
                                 out->pending_slot,
                                 sizeof(out->pending_slot))) {
        return VS_ERR_PARSE;
    }

    return VS_OK;
}

int vs_write(const char *path, const VersionInfo *info)
{
    if (!path || !info) return VS_ERR_INVALID;

    /* Validate: active_slot must be "A" or "B" */
    if (strcmp(info->active_slot, "A") != 0 &&
        strcmp(info->active_slot, "B") != 0) {
        return VS_ERR_INVALID;
    }

    /* pending_slot must be "A", "B", or "" */
    if (strlen(info->pending_slot) > 0 &&
        strcmp(info->pending_slot, "A") != 0 &&
        strcmp(info->pending_slot, "B") != 0) {
        return VS_ERR_INVALID;
    }

    /* Build JSON for pending_slot: null if empty, "X" otherwise */
    char pending_json[16];
    if (strlen(info->pending_slot) == 0) {
        snprintf(pending_json, sizeof(pending_json), "null");
    } else {
        snprintf(pending_json, sizeof(pending_json),
                 "\"%s\"", info->pending_slot);
    }

    /* Write to a temp file first (atomic write pattern) */
    char tmp_path[512];
    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", path);

    FILE *fp = fopen(tmp_path, "w");
    if (!fp) return VS_ERR_FILE;

    int written = fprintf(fp,
        "{\n"
        "  \"current_version\": \"%s\",\n"
        "  \"active_slot\":     \"%s\",\n"
        "  \"pending_slot\":    %s\n"
        "}\n",
        info->current_version,
        info->active_slot,
        pending_json
    );

    if (written < 0) {
        fclose(fp);
        remove(tmp_path);
        return VS_ERR_WRITE;
    }

    /* fflush + fclose before rename to guarantee data is on disk */
    if (fflush(fp) != 0 || fclose(fp) != 0) {
        remove(tmp_path);
        return VS_ERR_WRITE;
    }

    /* Rename temp → real (atomic on POSIX, near-atomic on NTFS) */
    if (portable_rename(tmp_path, path) != 0) {
        remove(tmp_path);
        return VS_ERR_WRITE;
    }

    return VS_OK;
}

void vs_print(const VersionInfo *info)
{
    if (!info) {
        printf("[version_store] (null)\n");
        return;
    }
    printf("[version_store] current_version=%s  active_slot=%s  pending_slot=%s\n",
           info->current_version,
           info->active_slot,
           (strlen(info->pending_slot) == 0) ? "null" : info->pending_slot);
}

const char *vs_strerror(int err)
{
    switch (err) {
        case VS_OK:          return "OK";
        case VS_ERR_FILE:    return "File open/create failed";
        case VS_ERR_PARSE:   return "JSON parse error (missing or malformed field)";
        case VS_ERR_INVALID: return "Invalid argument";
        case VS_ERR_WRITE:   return "Write to disk failed";
        default:             return "Unknown error";
    }
}
