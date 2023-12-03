#include <math.h>
#include <limits.h>

#include <vlc_common.h>
#include <vlc_plugin.h>
#include <vlc_aout.h>
#include <vlc_aout_volume.h>

static int Activate (vlc_object_t *);

vlc_module_begin ()
    set_subcategory (SUBCAT_AUDIO_AFILTER)
    set_description (N_("Integer audio volume"))
    set_capability ("audio volume", 9)
    set_callback(Activate)
vlc_module_end ()

static void FilterS32N (audio_volume_t *vol, block_t *block, float volume) {

}