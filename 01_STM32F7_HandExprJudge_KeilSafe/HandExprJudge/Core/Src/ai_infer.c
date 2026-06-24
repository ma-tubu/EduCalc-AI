#include "ai_infer.h"

#include <stdio.h>
#include "main.h"
#include "app_config.h"
#include "ai_platform.h"
#include "network.h"
#include "network_data.h"

const char *AIInfer_Labels[15] = {
  "0", "1", "2", "3", "4",
  "5", "6", "7", "8", "9",
  "+", "-", "*", "/", "="
};

static ai_handle s_network;
static ai_u8 s_activations[AI_NETWORK_DATA_ACTIVATIONS_SIZE];
static ai_buffer *s_input;
static ai_buffer *s_output;

void AIInfer_Init(void)
{
  ai_error err;
  const ai_handle act_addr[] = { s_activations };

  err = ai_network_create_and_init(&s_network, act_addr, NULL);
  if (err.type != AI_ERROR_NONE)
  {
    printf("ai_network_create error - type=%d code=%d\r\n", err.type, err.code);
    Error_Handler();
  }

  s_input = ai_network_inputs_get(s_network, NULL);
  s_output = ai_network_outputs_get(s_network, NULL);
}

uint32_t AIInfer_Run(float *input, float *output, float *confidence)
{
  uint32_t class_id = 0;
  float max_value = -1.0f;
  ai_i32 batch;
  ai_error err;

  s_input[0].data = AI_HANDLE_PTR(input);
  s_output[0].data = AI_HANDLE_PTR(output);

  batch = ai_network_run(s_network, s_input, s_output);
  if (batch != 1)
  {
    err = ai_network_get_error(s_network);
    printf("AI ai_network_run error - type=%d code=%d\r\n", err.type, err.code);
    Error_Handler();
  }

  for (uint32_t i = 0; i < AI_NETWORK_OUT_1_SIZE; i++)
  {
    if (max_value < output[i])
    {
      class_id = i;
      max_value = output[i];
    }
  }

  if (confidence != NULL)
  {
    *confidence = max_value;
  }

  return class_id;
}
