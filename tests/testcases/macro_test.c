


#define LOGIT(result)                                                 \
	if (result == ISC_R_NOMEMORY)                                 \
		(*callbacks->error)(callbacks, "dns_master_load: %s", \
				    isc_result_totext(result));       \
	else                                                          \
		(*callbacks->error)(callbacks, "%s: %s:%lu: %s",      \
				    "dns_master_load", source, line,  \
				    isc_result_totext(result))

struct dns_rdatacallbacks {
	unsigned int magic;

	/*%
	 * dns_load_master calls this when it has rdatasets to commit.
	 */
	dns_addrdatasetfunc_t add;

	/*%
	 * dns_master_load*() call this when loading a raw zonefile,
	 * to pass back information obtained from the file header
	 */
	dns_rawdatafunc_t rawdata;
	dns_zone_t	 *zone;

	/*%
	 * dns_load_master / dns_rdata_fromtext call this to issue a error.
	 */
	void (*error)(struct dns_rdatacallbacks *, const char *, ...);
	/*%
	 * dns_load_master / dns_rdata_fromtext call this to issue a warning.
	 */
	void (*warn)(struct dns_rdatacallbacks *, const char *, ...);
	/*%
	 * Private data handles for use by the above callback functions.
	 */
	void *add_private;
	void *error_private;
	void *warn_private;
};


typedef struct dns_rdatacallbacks dns_rdatacallbacks_t;

int main() {
    dns_rdatacallbacks_t *callbacks;
    isc_result_t result = ISC_R_UNEXPECTED;
    LOGIT(result);
    return 0;
}