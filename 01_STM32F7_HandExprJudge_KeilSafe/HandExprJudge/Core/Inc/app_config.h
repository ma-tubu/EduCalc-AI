#ifndef APP_CONFIG_H
#define APP_CONFIG_H

#include "network.h"

#define APP_RX_MAXLEN                 52000U
#define APP_EXPR_MAX_CHARS            7U
#define APP_EXPR_INPUT_SIZE           (AI_NETWORK_IN_1_SIZE * APP_EXPR_MAX_CHARS)
#define APP_RAW_INPUT_SIZE            12000U

#define APP_CONF_REWRITE_THRESHOLD    0.70f
#define APP_CONF_WARNING_THRESHOLD    0.85f
#define APP_IMAGE_HEADER_MARKER       (-1.0f)

#endif
