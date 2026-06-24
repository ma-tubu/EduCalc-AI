#ifndef APP_CONTROLLER_H
#define APP_CONTROLLER_H

#include <stdint.h>

void App_Init(void);
uint8_t *App_RxBuffer(void);
uint16_t App_RxBufferSize(void);
void App_OnUartRxEvent(uint16_t size);
uint8_t App_HasPendingFrame(void);
void App_ProcessPendingFrame(void);

#endif
