// (C) 2025 Brad Colbert

#ifndef __TIME_H__
#define __TIME_H__

#include <stdint.h>

void get_time_millis();
void cdecl set_time_millis(uint32_t millis);  // set time_millis global.
void sync_time(const char* url);

#endif // __TIME_H__