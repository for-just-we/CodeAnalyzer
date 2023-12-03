#ifndef CAIRO_PRIVATE_H
#define CAIRO_PRIVATE_H

#include "cairo-types-private.h"
#include "cairo-reference-count-private.h"

CAIRO_BEGIN_DECLS

struct _cairo {
    cairo_reference_count_t ref_count;
    cairo_status_t status;
    cairo_user_data_array_t user_data;

    const cairo_backend_t *backend;
};