#include "image_segment.h"

#include <stdio.h>
#include <string.h>
#include "app_config.h"

static uint32_t SegmentImage(float *image, uint32_t width, uint32_t height, float *chars, uint32_t max_chars);
static void CopyBoxTo28(float *image, uint32_t width, uint32_t height,
                        uint32_t x0, uint32_t x1, uint32_t y0, uint32_t y1,
                        float *dst);

float ImageSegment_NormalizePixel(float value)
{
  if (value < 0.0f)
  {
    return 0.0f;
  }
  if (value > 1.0f)
  {
    value = value / 255.0f;
  }
  if (value > 1.0f)
  {
    value = 1.0f;
  }
  return value;
}

uint32_t ImageSegment_InputToChars(float *raw_input, uint32_t value_count, float *chars, uint32_t max_chars)
{
  uint32_t char_count = 0;

  if ((value_count >= 4U) && (raw_input[0] < -0.5f))
  {
    uint32_t width = (uint32_t)(raw_input[1] + 0.5f);
    uint32_t height = (uint32_t)(raw_input[2] + 0.5f);
    uint32_t pixel_count = value_count - 3U;

    if ((width == 0U) || (height == 0U) || ((width * height) != pixel_count))
    {
      printf("Invalid image header. Use: -1 width height pixels...\r\n");
      return 0;
    }

    printf("input mode: header image %lux%lu, segmenting on board.\r\n",
           (unsigned long)width, (unsigned long)height);
    char_count = SegmentImage(&raw_input[3], width, height, chars, max_chars);
  }
  else if ((value_count % AI_NETWORK_IN_1_SIZE) == 0)
  {
    char_count = value_count / AI_NETWORK_IN_1_SIZE;
    if (char_count > max_chars)
    {
      printf("Invalid char count: %lu, max is %lu.\r\n", (unsigned long)char_count, (unsigned long)max_chars);
      return 0;
    }

    for (uint32_t i = 0; i < value_count; i++)
    {
      chars[i] = ImageSegment_NormalizePixel(raw_input[i]);
    }
    printf("input mode: fixed 28x28 blocks, chars=%lu\r\n", (unsigned long)char_count);
  }
  else if ((value_count % 28U) == 0)
  {
    uint32_t width = value_count / 28U;
    printf("input mode: inferred 28x%lu image, segmenting on board.\r\n", (unsigned long)width);
    char_count = SegmentImage(raw_input, width, 28U, chars, max_chars);
  }
  else
  {
    printf("Invalid input length. Need 784*N, 28*W, or -1 W H pixels.\r\n");
    return 0;
  }

  printf("segmented chars: %lu\r\n", (unsigned long)char_count);
  return char_count;
}

static uint32_t SegmentImage(float *image, uint32_t width, uint32_t height, float *chars, uint32_t max_chars)
{
  const float ink_threshold = 0.20f;
  const uint32_t required_blank_gap = 1U;
  uint32_t x = 0;
  uint32_t count = 0;

  while ((x < width) && (count < max_chars))
  {
    uint8_t has_ink = 0;
    for (uint32_t y = 0; y < height; y++)
    {
      if (ImageSegment_NormalizePixel(image[y * width + x]) > ink_threshold)
      {
        has_ink = 1;
        break;
      }
    }

    if (!has_ink)
    {
      x++;
      continue;
    }

    uint32_t x0 = x;
    uint32_t x1 = x;
    uint32_t blank_run = 0;

    while (x < width)
    {
      has_ink = 0;
      for (uint32_t y = 0; y < height; y++)
      {
        if (ImageSegment_NormalizePixel(image[y * width + x]) > ink_threshold)
        {
          has_ink = 1;
          break;
        }
      }

      if (has_ink)
      {
        blank_run = 0;
        x1 = x;
      }
      else
      {
        blank_run++;
        if (blank_run >= required_blank_gap)
        {
          break;
        }
      }
      x++;
    }

    uint32_t y0 = height;
    uint32_t y1 = 0;
    for (uint32_t yy = 0; yy < height; yy++)
    {
      for (uint32_t xx = x0; xx <= x1; xx++)
      {
        if (ImageSegment_NormalizePixel(image[yy * width + xx]) > ink_threshold)
        {
          if (yy < y0) y0 = yy;
          if (yy > y1) y1 = yy;
        }
      }
    }

    if (y0 <= y1)
    {
      CopyBoxTo28(image, width, height, x0, x1, y0, y1, &chars[count * AI_NETWORK_IN_1_SIZE]);
      printf("box[%lu]: x=%lu..%lu y=%lu..%lu size=%lux%lu\r\n",
             (unsigned long)count,
             (unsigned long)x0, (unsigned long)x1,
             (unsigned long)y0, (unsigned long)y1,
             (unsigned long)(x1 - x0 + 1U), (unsigned long)(y1 - y0 + 1U));
      count++;
    }

    if (blank_run >= required_blank_gap)
    {
      x++;
    }
  }

  return count;
}

static void CopyBoxTo28(float *image, uint32_t width, uint32_t height,
                        uint32_t x0, uint32_t x1, uint32_t y0, uint32_t y1,
                        float *dst)
{
  uint32_t box_w = x1 - x0 + 1U;
  uint32_t box_h = y1 - y0 + 1U;
  uint32_t out_w = box_w;
  uint32_t out_h = box_h;

  (void)height;
  memset(dst, 0, AI_NETWORK_IN_1_SIZE * sizeof(float));

  if ((box_w > 28U) || (box_h > 28U))
  {
    if (box_w >= box_h)
    {
      out_w = 28U;
      out_h = (box_h * 28U + box_w / 2U) / box_w;
      if (out_h == 0U) out_h = 1U;
    }
    else
    {
      out_h = 28U;
      out_w = (box_w * 28U + box_h / 2U) / box_h;
      if (out_w == 0U) out_w = 1U;
    }
  }

  if (out_w > 28U) out_w = 28U;
  if (out_h > 28U) out_h = 28U;

  uint32_t x_offset = (28U - out_w) / 2U;
  uint32_t y_offset = (28U - out_h) / 2U;

  for (uint32_t dy = 0; dy < out_h; dy++)
  {
    uint32_t sy = y0 + (dy * box_h) / out_h;
    for (uint32_t dx = 0; dx < out_w; dx++)
    {
      uint32_t sx = x0 + (dx * box_w) / out_w;
      dst[(y_offset + dy) * 28U + x_offset + dx] = ImageSegment_NormalizePixel(image[sy * width + sx]);
    }
  }
}
