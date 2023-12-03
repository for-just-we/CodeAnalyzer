#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sudoers.h>

#ifdef HAVE_STRLCPY
# define cpy_default	strlcpy
#else
# define cpy_default	sudo_strlcpy
#endif