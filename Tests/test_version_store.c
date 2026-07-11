/*
 * test_version_store.c
 *
 * Self-contained tests for version_store. No test framework required.
 * Compile and run — prints PASS / FAIL per test, exits 0 if all pass.
 *
 * Compile (Linux / macOS):
 *   gcc -Wall -Wextra -o test_vs test_version_store.c \
 *       ../Common/version_store/version_store.c -I../Common/version_store
 *
 * Compile (Windows MSVC):
 *   cl test_version_store.c ..\Common\version_store\version_store.c
 *       /I..\Common\version_store /W4
 */

#include "../Common/version_store/version_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -------------------------------------------------------------------------
 * Minimal test helpers
 * ---------------------------------------------------------------------- */

static int g_pass = 0;
static int g_fail = 0;

#define ASSERT_EQ_STR(label, expected, actual) do {               \
    if (strcmp((expected), (actual)) == 0) {                       \
        printf("  PASS  %s\n", (label));                           \
        g_pass++;                                                   \
    } else {                                                        \
        printf("  FAIL  %s — expected \"%s\", got \"%s\"\n",       \
               (label), (expected), (actual));                      \
        g_fail++;                                                   \
    }                                                               \
} while(0)

#define ASSERT_EQ_INT(label, expected, actual) do {               \
    if ((expected) == (actual)) {                                   \
        printf("  PASS  %s\n", (label));                           \
        g_pass++;                                                   \
    } else {                                                        \
        printf("  FAIL  %s — expected %d, got %d\n",               \
               (label), (expected), (actual));                      \
        g_fail++;                                                   \
    }                                                               \
} while(0)

/* -------------------------------------------------------------------------
 * Test helpers
 * ---------------------------------------------------------------------- */

/* Write raw bytes to a temp file — lets us test malformed input */
static void write_raw(const char *path, const char *content)
{
    FILE *fp = fopen(path, "w");
    if (!fp) { perror("write_raw"); exit(1); }
    fputs(content, fp);
    fclose(fp);
}

/* -------------------------------------------------------------------------
 * Tests
 * ---------------------------------------------------------------------- */

static void test_write_and_read_back(void)
{
    printf("\n[test] Write and read back — normal case\n");

    const char *path = "test_version_normal.json";

    VersionInfo w;
    memset(&w, 0, sizeof(w));
    strncpy(w.current_version, "1.0",  sizeof(w.current_version) - 1);
    strncpy(w.active_slot,     "A",    sizeof(w.active_slot) - 1);
    w.pending_slot[0] = '\0';   /* null */

    int rc = vs_write(path, &w);
    ASSERT_EQ_INT("vs_write returns VS_OK", VS_OK, rc);

    VersionInfo r;
    memset(&r, 0, sizeof(r));
    rc = vs_read(path, &r);
    ASSERT_EQ_INT("vs_read returns VS_OK", VS_OK, rc);
    ASSERT_EQ_STR("current_version round-trips", "1.0", r.current_version);
    ASSERT_EQ_STR("active_slot round-trips",     "A",   r.active_slot);
    ASSERT_EQ_STR("pending_slot is empty (null)", "",   r.pending_slot);

    remove(path);
}

static void test_write_and_read_with_pending(void)
{
    printf("\n[test] Write and read back — pending_slot set\n");

    const char *path = "test_version_pending.json";

    VersionInfo w;
    memset(&w, 0, sizeof(w));
    strncpy(w.current_version, "1.0", sizeof(w.current_version) - 1);
    strncpy(w.active_slot,     "A",   sizeof(w.active_slot) - 1);
    strncpy(w.pending_slot,    "B",   sizeof(w.pending_slot) - 1);

    int rc = vs_write(path, &w);
    ASSERT_EQ_INT("vs_write with pending_slot returns VS_OK", VS_OK, rc);

    VersionInfo r;
    memset(&r, 0, sizeof(r));
    rc = vs_read(path, &r);
    ASSERT_EQ_INT("vs_read returns VS_OK", VS_OK, rc);
    ASSERT_EQ_STR("current_version",  "1.0", r.current_version);
    ASSERT_EQ_STR("active_slot",      "A",   r.active_slot);
    ASSERT_EQ_STR("pending_slot",     "B",   r.pending_slot);

    remove(path);
}

static void test_json_output_format(void)
{
    printf("\n[test] JSON output is valid and pretty-printed\n");

    const char *path = "test_version_format.json";

    VersionInfo w;
    memset(&w, 0, sizeof(w));
    strncpy(w.current_version, "1.1", sizeof(w.current_version) - 1);
    strncpy(w.active_slot,     "B",   sizeof(w.active_slot) - 1);
    w.pending_slot[0] = '\0';

    vs_write(path, &w);

    /* Read raw bytes and check for expected JSON fragments */
    FILE *fp = fopen(path, "r");
    char buf[512];
    size_t n = fread(buf, 1, sizeof(buf)-1, fp);
    fclose(fp);
    buf[n] = '\0';

    int has_version = (strstr(buf, "\"current_version\": \"1.1\"") != NULL);
    int has_slot    = (strstr(buf, "\"active_slot\":     \"B\"")   != NULL);
    int has_null    = (strstr(buf, "\"pending_slot\":    null")    != NULL);

    ASSERT_EQ_INT("JSON contains current_version key+value", 1, has_version);
    ASSERT_EQ_INT("JSON contains active_slot key+value",     1, has_slot);
    ASSERT_EQ_INT("pending_slot serialises as null",         1, has_null);

    remove(path);
}

static void test_read_missing_file(void)
{
    printf("\n[test] Read non-existent file returns VS_ERR_FILE\n");

    VersionInfo r;
    int rc = vs_read("does_not_exist_xyz.json", &r);
    ASSERT_EQ_INT("vs_read missing file → VS_ERR_FILE", VS_ERR_FILE, rc);
}

static void test_read_malformed_json(void)
{
    printf("\n[test] Read malformed JSON returns VS_ERR_PARSE\n");

    const char *path = "test_malformed.json";
    write_raw(path, "{ this is not json }");

    VersionInfo r;
    int rc = vs_read(path, &r);
    ASSERT_EQ_INT("vs_read malformed → VS_ERR_PARSE", VS_ERR_PARSE, rc);

    remove(path);
}

static void test_read_missing_field(void)
{
    printf("\n[test] Read JSON missing active_slot returns VS_ERR_PARSE\n");

    const char *path = "test_missing_field.json";
    /* valid JSON but missing active_slot */
    write_raw(path,
        "{\n"
        "  \"current_version\": \"1.0\",\n"
        "  \"pending_slot\":    null\n"
        "}\n");

    VersionInfo r;
    int rc = vs_read(path, &r);
    ASSERT_EQ_INT("vs_read missing field → VS_ERR_PARSE", VS_ERR_PARSE, rc);

    remove(path);
}

static void test_write_invalid_slot(void)
{
    printf("\n[test] Write with invalid active_slot returns VS_ERR_INVALID\n");

    VersionInfo w;
    memset(&w, 0, sizeof(w));
    strncpy(w.current_version, "1.0", sizeof(w.current_version)-1);
    strncpy(w.active_slot,     "C",   sizeof(w.active_slot)-1);  /* invalid */

    int rc = vs_write("should_not_exist.json", &w);
    ASSERT_EQ_INT("vs_write bad slot → VS_ERR_INVALID", VS_ERR_INVALID, rc);
    remove("should_not_exist.json");  /* should not exist, but clean up anyway */
}

static void test_null_args(void)
{
    printf("\n[test] NULL args return VS_ERR_INVALID\n");

    VersionInfo v;
    ASSERT_EQ_INT("vs_read(NULL, &v)",  VS_ERR_INVALID, vs_read(NULL, &v));
    ASSERT_EQ_INT("vs_read(path, NULL)", VS_ERR_INVALID, vs_read("x", NULL));
    ASSERT_EQ_INT("vs_write(NULL, &v)", VS_ERR_INVALID, vs_write(NULL, &v));
    ASSERT_EQ_INT("vs_write(path, NULL)", VS_ERR_INVALID, vs_write("x", NULL));
}

static void test_version_11_slot_b(void)
{
    printf("\n[test] Version 1.1, slot B — the state after Phase 6 activate\n");

    const char *path = "test_version_11.json";

    VersionInfo w;
    memset(&w, 0, sizeof(w));
    strncpy(w.current_version, "1.1", sizeof(w.current_version)-1);
    strncpy(w.active_slot,     "B",   sizeof(w.active_slot)-1);
    w.pending_slot[0] = '\0';

    vs_write(path, &w);

    VersionInfo r;
    memset(&r, 0, sizeof(r));
    vs_read(path, &r);

    ASSERT_EQ_STR("version 1.1 stored and read back", "1.1", r.current_version);
    ASSERT_EQ_STR("active_slot B stored and read back", "B", r.active_slot);
    ASSERT_EQ_STR("pending_slot null after activate",   "",  r.pending_slot);

    remove(path);
}

/* -------------------------------------------------------------------------
 * Entry point
 * ---------------------------------------------------------------------- */

int main(void)
{
    printf("=== version_store tests ===\n");

    test_write_and_read_back();
    test_write_and_read_with_pending();
    test_json_output_format();
    test_read_missing_file();
    test_read_malformed_json();
    test_read_missing_field();
    test_write_invalid_slot();
    test_null_args();
    test_version_11_slot_b();

    printf("\n=== Results: %d passed, %d failed ===\n", g_pass, g_fail);
    return (g_fail == 0) ? 0 : 1;
}
