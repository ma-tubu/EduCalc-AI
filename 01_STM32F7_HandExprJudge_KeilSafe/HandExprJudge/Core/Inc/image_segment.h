#ifndef IMAGE_SEGMENT_H
#define IMAGE_SEGMENT_H

#include <stdint.h>

float ImageSegment_NormalizePixel(float value);
uint32_t ImageSegment_InputToChars(float *raw_input, uint32_t value_count, float *chars, uint32_t max_chars);

#endif
