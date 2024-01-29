

#define gmp_alloc(size) ((*gmp_allocate_func)((size)))

static mp_ptr
gmp_alloc_limbs (mp_size_t size)
{
    gmp_alloc (size * sizeof (mp_limb_t));
}