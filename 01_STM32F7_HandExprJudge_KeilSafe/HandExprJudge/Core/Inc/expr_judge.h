#ifndef EXPR_JUDGE_H
#define EXPR_JUDGE_H

#include <stdint.h>

typedef enum
{
  EXPR_JUDGE_ONLY_RECOGNIZED = 0,
  EXPR_JUDGE_INVALID_LEFT_NUMBER,
  EXPR_JUDGE_INVALID_OPERATOR,
  EXPR_JUDGE_INVALID_RIGHT_NUMBER,
  EXPR_JUDGE_INVALID_EQUAL,
  EXPR_JUDGE_INVALID_ANSWER,
  EXPR_JUDGE_INVALID_TAIL,
  EXPR_JUDGE_INVALID_OPERATOR_OR_DIVISION,
  EXPR_JUDGE_CORRECT,
  EXPR_JUDGE_WRONG
} ExprJudge_Status_t;

typedef struct
{
  int left;
  int right;
  int user_answer;
  int correct_answer;
  char op;
  uint32_t answer_start_index;
  uint32_t answer_len;
} ExprJudge_Result_t;

ExprJudge_Status_t ExprJudge_Run(const char *expr, uint32_t len, ExprJudge_Result_t *result);
const char *ExprJudge_StatusName(ExprJudge_Status_t status);

#endif
