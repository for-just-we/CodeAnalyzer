const pg_wchar_tbl pg_wchar_table[] = {
	{pg_ascii2wchar_with_len, pg_wchar2single_with_len, pg_ascii_mblen, pg_ascii_dsplen, pg_ascii_verifychar, pg_ascii_verifystr, 1},	/* PG_SQL_ASCII */
	{pg_eucjp2wchar_with_len, pg_wchar2euc_with_len, pg_eucjp_mblen, pg_eucjp_dsplen, pg_eucjp_verifychar, pg_eucjp_verifystr, 3},	/* PG_EUC_JP */
	{pg_euccn2wchar_with_len, pg_wchar2euc_with_len, pg_euccn_mblen, pg_euccn_dsplen, pg_euccn_verifychar, pg_euccn_verifystr, 2},	/* PG_EUC_CN */
	{pg_euckr2wchar_with_len, pg_wchar2euc_with_len, pg_euckr_mblen, pg_euckr_dsplen, pg_euckr_verifychar, pg_euckr_verifystr, 3},	/* PG_EUC_KR */
	{pg_euctw2wchar_with_len, pg_wchar2euc_with_len, pg_euctw_mblen, pg_euctw_dsplen, pg_euctw_verifychar, pg_euctw_verifystr, 4},	/* PG_EUC_TW */
	{pg_eucjp2wchar_with_len, pg_wchar2euc_with_len, pg_eucjp_mblen, pg_eucjp_dsplen, pg_eucjp_verifychar, pg_eucjp_verifystr, 3},	/* PG_EUC_JIS_2004 */
	{pg_utf2wchar_with_len, pg_wchar2utf_with_len, pg_utf_mblen, pg_utf_dsplen, pg_utf8_verifychar, pg_utf8_verifystr, 4},	/* PG_UTF8 */
	{pg_mule2wchar_with_len, pg_wchar2mule_with_len, pg_mule_mblen, pg_mule_dsplen, pg_mule_verifychar, pg_mule_verifystr, 4},	/* PG_MULE_INTERNAL */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN1 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN2 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN3 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN4 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN5 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN6 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN7 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN8 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN9 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_LATIN10 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1256 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1258 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN866 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN874 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_KOI8R */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1251 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1252 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* ISO-8859-5 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* ISO-8859-6 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* ISO-8859-7 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* ISO-8859-8 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1250 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1253 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1254 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1255 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_WIN1257 */
	{pg_latin12wchar_with_len, pg_wchar2single_with_len, pg_latin1_mblen, pg_latin1_dsplen, pg_latin1_verifychar, pg_latin1_verifystr, 1},	/* PG_KOI8U */
	{0, 0, pg_sjis_mblen, pg_sjis_dsplen, pg_sjis_verifychar, pg_sjis_verifystr, 2},	/* PG_SJIS */
	{0, 0, pg_big5_mblen, pg_big5_dsplen, pg_big5_verifychar, pg_big5_verifystr, 2},	/* PG_BIG5 */
	{0, 0, pg_gbk_mblen, pg_gbk_dsplen, pg_gbk_verifychar, pg_gbk_verifystr, 2},	/* PG_GBK */
	{0, 0, pg_uhc_mblen, pg_uhc_dsplen, pg_uhc_verifychar, pg_uhc_verifystr, 2},	/* PG_UHC */
	{0, 0, pg_gb18030_mblen, pg_gb18030_dsplen, pg_gb18030_verifychar, pg_gb18030_verifystr, 4},	/* PG_GB18030 */
	{0, 0, pg_johab_mblen, pg_johab_dsplen, pg_johab_verifychar, pg_johab_verifystr, 3},	/* PG_JOHAB */
	{0, 0, pg_sjis_mblen, pg_sjis_dsplen, pg_sjis_verifychar, pg_sjis_verifystr, 2} /* PG_SHIFT_JIS_2004 */
};


extern PGDLLIMPORT const pg_wchar_tbl pg_wchar_table[];