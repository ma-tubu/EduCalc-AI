#include "app_controller.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "app_config.h"
#include "ai_infer.h"
#include "expr_judge.h"
#include "image_segment.h"
#include "network.h"

typedef struct
{
  uint8_t RxBuf[APP_RX_MAXLEN];
  uint16_t RxLen;
  uint8_t RxFlag;
} UartRx_t;

typedef enum
{
  APP_WAIT_EXPRESSION = 0,
  APP_WAIT_REWRITE_COMMAND,
  APP_WAIT_REWRITE_INDEX,
  APP_WAIT_REWRITE_CHAR_PAYLOAD,
  APP_WAIT_WRONG_ANSWER_COMMAND,
  APP_WAIT_REWRITE_ANSWER_PAYLOAD
} AppState_t;

static UartRx_t s_uart_rx;
static AppState_t s_state = APP_WAIT_EXPRESSION;

static float s_raw_input[APP_RAW_INPUT_SIZE];
static float s_char_data[APP_EXPR_INPUT_SIZE];
static float s_tmp_char_data[APP_EXPR_INPUT_SIZE];
static float s_ai_output[AI_NETWORK_OUT_1_SIZE];

static uint32_t s_last_char_count;
static char s_last_expr[APP_EXPR_MAX_CHARS + 1U];
static float s_last_confidence[APP_EXPR_MAX_CHARS];
static uint32_t s_low_conf_indexes[APP_EXPR_MAX_CHARS];
static uint32_t s_low_conf_count;
static uint32_t s_rewrite_index;
static uint32_t s_answer_start_index;
static uint32_t s_answer_len;

static void ResetState(void);
static uint8_t GetCommandChar(char *buf, char *cmd);
static uint8_t HandleCommandFrame(char *buf);
static void PrintRewriteMenu(void);
static void ProcessInput(uint32_t value_count);
static void ProcessRewriteChar(uint32_t value_count);
static void ProcessRewriteAnswer(uint32_t value_count);
static void RecognizeCurrentChars(void);
static void JudgeExpression(void);
static void StartAnswerRewrite(void);

void App_Init(void)
{
  memset(&s_uart_rx, 0, sizeof(s_uart_rx));
  ResetState();
  AIInfer_Init();
}

uint8_t *App_RxBuffer(void)
{
  return s_uart_rx.RxBuf;
}

uint16_t App_RxBufferSize(void)
{
  return (uint16_t)APP_RX_MAXLEN;
}

void App_OnUartRxEvent(uint16_t size)
{
  s_uart_rx.RxLen = size;
  if (size < APP_RX_MAXLEN)
  {
    s_uart_rx.RxBuf[size] = 0;
  }
  s_uart_rx.RxFlag = 1;
}

uint8_t App_HasPendingFrame(void)
{
  return s_uart_rx.RxFlag;
}

void App_ProcessPendingFrame(void)
{
  char *p;
  uint32_t i = 0;

  s_uart_rx.RxFlag = 0;

  if (HandleCommandFrame((char *)s_uart_rx.RxBuf))
  {
    memset(s_uart_rx.RxBuf, 0, APP_RX_MAXLEN);
    return;
  }

  p = strtok((char *)s_uart_rx.RxBuf, " \r\n\t,");
  while ((p != NULL) && (i < APP_RAW_INPUT_SIZE))
  {
    s_raw_input[i] = (float)atof(p);
    p = strtok(NULL, " \r\n\t,");
    i++;
  }

  printf("\r\nYou Have Received %lu Numbers\r\n", (unsigned long)i);

  if (p != NULL)
  {
    printf("Input too long. Max is %lu numbers.\r\n", (unsigned long)APP_RAW_INPUT_SIZE);
  }
  else if (s_state == APP_WAIT_REWRITE_CHAR_PAYLOAD)
  {
    ProcessRewriteChar(i);
  }
  else if (s_state == APP_WAIT_REWRITE_ANSWER_PAYLOAD)
  {
    ProcessRewriteAnswer(i);
  }
  else if (s_state == APP_WAIT_REWRITE_COMMAND)
  {
    printf("please enter command first: 0=rewrite unclear char, 1=rewrite all, 2=reset.\r\n");
    PrintRewriteMenu();
  }
  else if (s_state == APP_WAIT_REWRITE_INDEX)
  {
    printf("please enter char index first: ");
    for (uint32_t k = 0; k < s_low_conf_count; k++)
    {
      printf("%lu%s", (unsigned long)s_low_conf_indexes[k], (k + 1U == s_low_conf_count) ? "\r\n" : ", ");
    }
  }
  else if (s_state == APP_WAIT_WRONG_ANSWER_COMMAND)
  {
    printf("please enter command first: 0=rewrite answer, 1=rewrite all, 2=reset.\r\n");
  }
  else
  {
    ProcessInput(i);
  }

  memset(s_uart_rx.RxBuf, 0, APP_RX_MAXLEN);
}

static void ResetState(void)
{
  s_state = APP_WAIT_EXPRESSION;
  s_last_char_count = 0;
  s_low_conf_count = 0;
  s_rewrite_index = 0;
  s_answer_start_index = 0;
  s_answer_len = 0;
  memset(s_last_expr, 0, sizeof(s_last_expr));
  memset(s_last_confidence, 0, sizeof(s_last_confidence));
  memset(s_low_conf_indexes, 0, sizeof(s_low_conf_indexes));
}

static uint8_t GetCommandChar(char *buf, char *cmd)
{
  char *p = buf;
  while ((*p == ' ') || (*p == '\r') || (*p == '\n') || (*p == '\t') || (*p == ','))
  {
    p++;
  }

  if ((*p < '0') || (*p > '9'))
  {
    return 0;
  }
  *cmd = *p++;

  while ((*p == ' ') || (*p == '\r') || (*p == '\n') || (*p == '\t') || (*p == ','))
  {
    p++;
  }

  return (*p == '\0') ? 1U : 0U;
}

static uint8_t HandleCommandFrame(char *buf)
{
  char cmd;

  if (!GetCommandChar(buf, &cmd))
  {
    return 0;
  }

  if (s_state == APP_WAIT_REWRITE_COMMAND)
  {
    if (cmd == '0')
    {
      if (s_low_conf_count == 1U)
      {
        s_rewrite_index = s_low_conf_indexes[0];
        s_state = APP_WAIT_REWRITE_CHAR_PAYLOAD;
        printf("rewrite char[%lu]. Please send one rewritten character image.\r\n", (unsigned long)s_rewrite_index);
      }
      else
      {
        s_state = APP_WAIT_REWRITE_INDEX;
        printf("multiple low-confidence chars. Enter char index to rewrite: ");
        for (uint32_t i = 0; i < s_low_conf_count; i++)
        {
          printf("%lu%s", (unsigned long)s_low_conf_indexes[i], (i + 1U == s_low_conf_count) ? "\r\n" : ", ");
        }
      }
      return 1;
    }
    if (cmd == '1')
    {
      s_state = APP_WAIT_EXPRESSION;
      printf("rewrite all: please send the whole expression again.\r\n");
      return 1;
    }
    if (cmd == '2')
    {
      ResetState();
      printf("reset: ready for next expression.\r\n");
      return 1;
    }

    printf("invalid command. Use 0=rewrite char, 1=rewrite all, 2=reset.\r\n");
    PrintRewriteMenu();
    return 1;
  }

  if (s_state == APP_WAIT_REWRITE_INDEX)
  {
    uint32_t idx = (uint32_t)(cmd - '0');
    uint8_t ok = 0;

    for (uint32_t i = 0; i < s_low_conf_count; i++)
    {
      if (s_low_conf_indexes[i] == idx)
      {
        ok = 1;
        break;
      }
    }

    if (ok)
    {
      s_rewrite_index = idx;
      s_state = APP_WAIT_REWRITE_CHAR_PAYLOAD;
      printf("rewrite char[%lu]. Please send one rewritten character image.\r\n", (unsigned long)s_rewrite_index);
    }
    else if (cmd == '1')
    {
      s_state = APP_WAIT_EXPRESSION;
      printf("rewrite all: please send the whole expression again.\r\n");
    }
    else if (cmd == '2')
    {
      ResetState();
      printf("reset: ready for next expression.\r\n");
    }
    else
    {
      printf("invalid index. Please enter one of: ");
      for (uint32_t i = 0; i < s_low_conf_count; i++)
      {
        printf("%lu%s", (unsigned long)s_low_conf_indexes[i], (i + 1U == s_low_conf_count) ? "\r\n" : ", ");
      }
    }
    return 1;
  }

  if ((s_state == APP_WAIT_REWRITE_CHAR_PAYLOAD) || (s_state == APP_WAIT_REWRITE_ANSWER_PAYLOAD))
  {
    if (cmd == '1')
    {
      s_state = APP_WAIT_EXPRESSION;
      printf("rewrite all: please send the whole expression again.\r\n");
      return 1;
    }
    if (cmd == '2')
    {
      ResetState();
      printf("reset: ready for next expression.\r\n");
      return 1;
    }
    return 0;
  }

  if (s_state == APP_WAIT_WRONG_ANSWER_COMMAND)
  {
    if (cmd == '0')
    {
      StartAnswerRewrite();
      return 1;
    }
    if (cmd == '1')
    {
      s_state = APP_WAIT_EXPRESSION;
      printf("rewrite all: please send the whole expression again.\r\n");
      return 1;
    }
    if (cmd == '2')
    {
      ResetState();
      printf("reset: ready for next expression.\r\n");
      return 1;
    }

    printf("invalid command. Use 0=rewrite answer, 1=rewrite all, 2=reset.\r\n");
    return 1;
  }

  return 0;
}

static void PrintRewriteMenu(void)
{
  printf("low confidence detected.\r\n");
  for (uint32_t i = 0; i < s_low_conf_count; i++)
  {
    uint32_t idx = s_low_conf_indexes[i];
    printf("char[%lu]=%c confidence=%.3f: not clear, please rewrite.\r\n",
           (unsigned long)idx, s_last_expr[idx], s_last_confidence[idx]);
  }
  printf("command 0: rewrite unclear char%s\r\n", (s_low_conf_count > 1U) ? " (then choose index)" : "");
  printf("command 1: rewrite whole expression\r\n");
  printf("command 2: reset for next expression\r\n");
}

static void ProcessInput(uint32_t value_count)
{
  if (value_count == 0U)
  {
    printf("Invalid input: empty frame.\r\n");
    return;
  }

  memset(s_char_data, 0, sizeof(s_char_data));
  s_last_char_count = ImageSegment_InputToChars(s_raw_input, value_count, s_char_data, APP_EXPR_MAX_CHARS);

  if ((s_last_char_count == 0U) || (s_last_char_count > APP_EXPR_MAX_CHARS))
  {
    printf("Invalid char count: %lu\r\n", (unsigned long)s_last_char_count);
    return;
  }

  RecognizeCurrentChars();
}

static void ProcessRewriteChar(uint32_t value_count)
{
  uint32_t char_count;

  if (s_rewrite_index >= s_last_char_count)
  {
    printf("rewrite index invalid, reset.\r\n");
    ResetState();
    return;
  }

  memset(s_tmp_char_data, 0, sizeof(s_tmp_char_data));
  char_count = ImageSegment_InputToChars(s_raw_input, value_count, s_tmp_char_data, 1U);
  if (char_count != 1U)
  {
    printf("rewrite failed: please send exactly one character image.\r\n");
    s_state = APP_WAIT_REWRITE_CHAR_PAYLOAD;
    return;
  }

  memcpy(&s_char_data[s_rewrite_index * AI_NETWORK_IN_1_SIZE], s_tmp_char_data, AI_NETWORK_IN_1_SIZE * sizeof(float));
  printf("char[%lu] updated. Re-recognizing expression.\r\n", (unsigned long)s_rewrite_index);
  s_state = APP_WAIT_EXPRESSION;
  RecognizeCurrentChars();
}

static void StartAnswerRewrite(void)
{
  if ((s_answer_start_index == 0U) || (s_answer_start_index >= s_last_char_count) || (s_answer_len == 0U))
  {
    printf("cannot locate answer chars, please rewrite whole expression.\r\n");
    s_state = APP_WAIT_EXPRESSION;
    return;
  }

  s_state = APP_WAIT_REWRITE_ANSWER_PAYLOAD;
  printf("rewrite answer. Please send the whole answer image (%lu char%s expected).\r\n",
         (unsigned long)s_answer_len, (s_answer_len > 1U) ? "s" : "");
}

static void ProcessRewriteAnswer(uint32_t value_count)
{
  uint32_t char_count;

  if ((s_answer_start_index == 0U) || (s_answer_start_index >= s_last_char_count))
  {
    printf("answer position invalid, reset.\r\n");
    ResetState();
    return;
  }

  memset(s_tmp_char_data, 0, sizeof(s_tmp_char_data));
  char_count = ImageSegment_InputToChars(s_raw_input, value_count, s_tmp_char_data, APP_EXPR_MAX_CHARS - s_answer_start_index);
  if (char_count == 0U)
  {
    printf("rewrite answer failed: please send answer image.\r\n");
    s_state = APP_WAIT_REWRITE_ANSWER_PAYLOAD;
    return;
  }

  for (uint32_t i = 0; i < char_count; i++)
  {
    memcpy(&s_char_data[(s_answer_start_index + i) * AI_NETWORK_IN_1_SIZE],
           &s_tmp_char_data[i * AI_NETWORK_IN_1_SIZE],
           AI_NETWORK_IN_1_SIZE * sizeof(float));
  }

  s_last_char_count = s_answer_start_index + char_count;
  printf("answer updated with %lu char%s. Re-recognizing expression.\r\n",
         (unsigned long)char_count, (char_count > 1U) ? "s" : "");
  s_state = APP_WAIT_EXPRESSION;
  RecognizeCurrentChars();
}

static void RecognizeCurrentChars(void)
{
  s_low_conf_count = 0;

  for (uint32_t c = 0; c < s_last_char_count; c++)
  {
    uint32_t class_id = AIInfer_Run(&s_char_data[c * AI_NETWORK_IN_1_SIZE], s_ai_output, &s_last_confidence[c]);
    s_last_expr[c] = AIInfer_Labels[class_id][0];
    printf("char[%lu]: label=%s confidence=%.3f\r\n",
           (unsigned long)c, AIInfer_Labels[class_id], s_last_confidence[c]);

    if (s_last_confidence[c] < APP_CONF_REWRITE_THRESHOLD)
    {
      s_low_conf_indexes[s_low_conf_count++] = c;
    }
    else if (s_last_confidence[c] < APP_CONF_WARNING_THRESHOLD)
    {
      printf("warning: char[%lu] confidence is not high.\r\n", (unsigned long)c);
    }
  }

  s_last_expr[s_last_char_count] = '\0';
  printf("recognized expression: %s\r\n", s_last_expr);

  if (s_low_conf_count > 0U)
  {
    s_state = APP_WAIT_REWRITE_COMMAND;
    PrintRewriteMenu();
    return;
  }

  s_state = APP_WAIT_EXPRESSION;
  JudgeExpression();
}

static void JudgeExpression(void)
{
  ExprJudge_Result_t result;
  ExprJudge_Status_t status;

  status = ExprJudge_Run(s_last_expr, s_last_char_count, &result);

  if ((status == EXPR_JUDGE_CORRECT) || (status == EXPR_JUDGE_WRONG))
  {
    printf("calculated answer: %d\r\n", result.correct_answer);
    printf("user answer: %d\r\n", result.user_answer);
  }

  printf("judge: %s\r\n", ExprJudge_StatusName(status));

  if (status == EXPR_JUDGE_CORRECT)
  {
    s_state = APP_WAIT_EXPRESSION;
  }
  else if (status == EXPR_JUDGE_WRONG)
  {
    s_answer_start_index = result.answer_start_index;
    s_answer_len = result.answer_len;
    s_state = APP_WAIT_WRONG_ANSWER_COMMAND;
    printf("tip: answer is wrong, please rewrite result.\r\n");
    printf("command 0: rewrite answer result\r\n");
    printf("command 1: rewrite whole expression\r\n");
    printf("command 2: reset for next expression\r\n");
  }
}
