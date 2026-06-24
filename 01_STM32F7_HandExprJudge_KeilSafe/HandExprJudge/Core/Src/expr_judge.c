#include "expr_judge.h"

#include <string.h>

static uint8_t IsDigit(char ch)
{
  return (uint8_t)((ch >= '0') && (ch <= '9'));
}

ExprJudge_Status_t ExprJudge_Run(const char *expr, uint32_t len, ExprJudge_Result_t *result)
{
  uint32_t idx = 0;
  uint8_t valid = 1;
  uint8_t answer_negative = 0;
  int a = 0;
  int b = 0;
  int user_answer = 0;
  int correct_answer = 0;
  char op;

  if (result != NULL)
  {
    memset(result, 0, sizeof(*result));
  }

  if (len < 5U)
  {
    return EXPR_JUDGE_ONLY_RECOGNIZED;
  }

  if ((idx >= len) || !IsDigit(expr[idx]))
  {
    return EXPR_JUDGE_INVALID_LEFT_NUMBER;
  }
  while ((idx < len) && IsDigit(expr[idx]))
  {
    a = a * 10 + (expr[idx] - '0');
    idx++;
  }

  if ((idx >= len) || ((expr[idx] != '+') && (expr[idx] != '-') && (expr[idx] != '*') && (expr[idx] != '/')))
  {
    return EXPR_JUDGE_INVALID_OPERATOR;
  }
  op = expr[idx++];

  if ((idx >= len) || !IsDigit(expr[idx]))
  {
    return EXPR_JUDGE_INVALID_RIGHT_NUMBER;
  }
  while ((idx < len) && IsDigit(expr[idx]))
  {
    b = b * 10 + (expr[idx] - '0');
    idx++;
  }

  if ((idx >= len) || (expr[idx] != '='))
  {
    return EXPR_JUDGE_INVALID_EQUAL;
  }
  idx++;

  uint32_t answer_start = idx;
  if ((idx < len) && (expr[idx] == '-'))
  {
    answer_negative = 1;
    idx++;
  }

  if ((idx >= len) || !IsDigit(expr[idx]))
  {
    return EXPR_JUDGE_INVALID_ANSWER;
  }
  while ((idx < len) && IsDigit(expr[idx]))
  {
    user_answer = user_answer * 10 + (expr[idx] - '0');
    idx++;
  }

  if (idx != len)
  {
    return EXPR_JUDGE_INVALID_TAIL;
  }

  if (answer_negative)
  {
    user_answer = -user_answer;
  }

  switch (op)
  {
    case '+':
      correct_answer = a + b;
      break;
    case '-':
      correct_answer = a - b;
      break;
    case '*':
      correct_answer = a * b;
      break;
    case '/':
      if ((b == 0) || ((a % b) != 0))
      {
        valid = 0;
      }
      else
      {
        correct_answer = a / b;
      }
      break;
    default:
      valid = 0;
      break;
  }

  if (!valid)
  {
    return EXPR_JUDGE_INVALID_OPERATOR_OR_DIVISION;
  }

  if (result != NULL)
  {
    result->left = a;
    result->right = b;
    result->user_answer = user_answer;
    result->correct_answer = correct_answer;
    result->op = op;
    result->answer_start_index = answer_start;
    result->answer_len = len - answer_start;
  }

  return (user_answer == correct_answer) ? EXPR_JUDGE_CORRECT : EXPR_JUDGE_WRONG;
}

const char *ExprJudge_StatusName(ExprJudge_Status_t status)
{
  switch (status)
  {
    case EXPR_JUDGE_ONLY_RECOGNIZED:
      return "ONLY_RECOGNIZED_NO_EXPRESSION";
    case EXPR_JUDGE_INVALID_LEFT_NUMBER:
      return "INVALID_LEFT_NUMBER";
    case EXPR_JUDGE_INVALID_OPERATOR:
      return "INVALID_OPERATOR";
    case EXPR_JUDGE_INVALID_RIGHT_NUMBER:
      return "INVALID_RIGHT_NUMBER";
    case EXPR_JUDGE_INVALID_EQUAL:
      return "INVALID_EQUAL";
    case EXPR_JUDGE_INVALID_ANSWER:
      return "INVALID_ANSWER";
    case EXPR_JUDGE_INVALID_TAIL:
      return "INVALID_TAIL";
    case EXPR_JUDGE_INVALID_OPERATOR_OR_DIVISION:
      return "INVALID_OPERATOR_OR_DIVISION";
    case EXPR_JUDGE_CORRECT:
      return "CORRECT";
    case EXPR_JUDGE_WRONG:
      return "WRONG";
    default:
      return "UNKNOWN";
  }
}
