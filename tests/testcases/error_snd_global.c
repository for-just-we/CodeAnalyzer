/*
这个case中宏定义会被正确解析，
但是typedef SF_CART_INFO_VAR (256) SF_CART_INFO ;
引用了宏导致下面所有的类型定义语句都被错误解析
*/

#define	SF_CART_INFO_VAR(p_tag_text_size) \
			struct \
			{	char		version [4] ; \
				char		title [64] ; \
				char		artist [64] ; \
				char		cut_id [64] ; \
				char		client_id [64] ; \
				char		category [64] ; \
				char		classification [64] ; \
				char		out_cue [64] ; \
				char		start_date [10] ; \
				char		start_time [8] ; \
				char		end_date [10] ; \
				char		end_time [8] ; \
				char		producer_app_id [64] ; \
				char		producer_app_version [64] ; \
				char		user_def [64] ; \
				int32_t		level_reference ; \
				SF_CART_TIMER	post_timers [8] ; \
				char		reserved [276] ; \
				char		url [1024] ; \
				uint32_t	tag_text_size ; \
				char		tag_text [p_tag_text_size] ; \
			}

typedef SF_CART_INFO_VAR (256) SF_CART_INFO ;

/*	Virtual I/O functionality. */

typedef sf_count_t		(*sf_vio_get_filelen)	(void *user_data) ;
typedef sf_count_t		(*sf_vio_seek)		(sf_count_t offset, int whence, void *user_data) ;
typedef sf_count_t		(*sf_vio_read)		(void *ptr, sf_count_t count, void *user_data) ;
typedef sf_count_t		(*sf_vio_write)		(const void *ptr, sf_count_t count, void *user_data) ;
typedef sf_count_t		(*sf_vio_tell)		(void *user_data) ;

struct SF_VIRTUAL_IO
{	sf_vio_get_filelen	get_filelen ;
	sf_vio_seek			seek ;
	sf_vio_read			read ;
	sf_vio_write		write ;
	sf_vio_tell			tell ;
} ;

typedef	struct SF_VIRTUAL_IO SF_VIRTUAL_IO ;
