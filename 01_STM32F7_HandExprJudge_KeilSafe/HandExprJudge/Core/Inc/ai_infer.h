#ifndef AI_INFER_H
#define AI_INFER_H

#include <stdint.h>

extern const char *AIInfer_Labels[15];

void AIInfer_Init(void);
uint32_t AIInfer_Run(float *input, float *output, float *confidence);

#endif
