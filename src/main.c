// (C) 2025 Brad Colbert

#include "time.h"

#include <fujinet-network.h>

#include <conio.h>

#include <stdio.h>
#include <stdint.h>

extern uint32_t time_millis = 0x00000000;

typedef struct _time_packet {
    uint32_t t_ms; // Time in milliseconds
    uint16_t sequence;
    uint8_t msg_type;
} TimePacket;

void sync_time(const char* url)
{
    uint32_t t1, t2, t3, t4, RTT;
    uint32_t t2_t1, t3_t4, t21_t34, new_time;
    int16_t num_bytes;
    TimePacket time_packet;

hack:
do {
    // Initialize the time packet
    time_packet.sequence = 0;
    time_packet.msg_type = 't';

    // T1
    get_time_millis();
    time_packet.t_ms = t1 = time_millis; // Store the current time in milliseconds

    printf("t1 %ld, %d, %c\n", time_packet.t_ms, time_packet.sequence, time_packet.msg_type);

    // Send the a packet to the server.  Doesn't matter what is in it.  It just triggers
    // the server to send one back with it's time.
    if(FN_ERR_OK != network_write((char*)url, (uint8_t*)&time_packet, (uint16_t)sizeof(TimePacket)))
    {
        printf("Unable to write time request\n");
        //goto hack;
        return;
    }

    // Read T2 from server (represents round trip time)
    num_bytes = network_read((char*)url, (uint8_t*)&time_packet, (uint16_t)sizeof(TimePacket));
    if(num_bytes < sizeof(TimePacket))
    {
        printf("Unable to read T2 request\n");
        //goto hack;
        return;
    }

    if(time_packet.sequence != 1)
    {
        printf("Invalid sequence number !1 %d\n", time_packet.sequence);
        //goto hack;
        return;
    }

    t2 = time_packet.t_ms; // Store the server's time in milliseconds

    printf("t2 %ld, %ld, %d, %c\n", time_millis, time_packet.t_ms, time_packet.sequence, time_packet.msg_type);

    // Read T3 from server (represents server to client time)
    num_bytes = network_read((char*)url, (uint8_t*)&time_packet, (uint16_t)sizeof(TimePacket));
    if(num_bytes < sizeof(TimePacket))
    {
        printf("Unable to read T3 request\n");
        //goto hack; // Retry if we didn't get a full packet
        return;
    }

    // T4  (get as soon as possible)
    get_time_millis();
    t4 = time_millis; // Store the current time in milliseconds

    if(time_packet.sequence != 2)
    {
        printf("Invalid sequence number !2 %d\n", time_packet.sequence);
        //goto hack;
        return;
    }

    // T3
    t3 = time_packet.t_ms; // Store the server's time in milliseconds

    printf("t3 %ld, %ld, %d, %d\n", time_millis, time_packet.t_ms, time_packet.sequence, time_packet.msg_type);

    // Calculate the round trip time
    // t2_t1 = t2 - t1;
    // t3_t4 = t3 - t4;
    // t21_t34 = t2_t1 - t3_t4;
    // offset = t21_t34 >> 1; // / (int32_t)2;
    t2_t1 = t2 - t1; // Time from T1 to T2 3485752
    t3_t4 = t3 - t4; // Time from T3 to T4 3485576
    RTT = (t4 - t1) - (t3 - t2); // Round trip time
    t21_t34 = (t2_t1 + t3_t4) / 2; // Average of the two round trip times
    new_time = t4 + t21_t34;
    set_time_millis(new_time);

    printf("RTT: %ldms\n", RTT);
    printf("Time from T1 to T2: %ldms\n", t2_t1);
    printf("Time from T3 to T4: %ldms\n", t3_t4);
    printf("Delta: %ldms\n", t21_t34);
    printf("Updated time: %ldms %ldms\n", t4, time_millis);
    printf("Any key to continue.\n");


} while(27 != cgetc()); // Wait for ESC key to exit

    // cprintf("A:%08X B:%08X\n", as_int32(t1), as_int32(t2));
    // cprintf("C:%08X D:%08X\n", as_int32(t3), as_int32(t4));

    //cprintf("RTT: %ld, Offset: %ld\n", rtt, offset);
    //cprintf("T: %ld Offset: %ld\n", as_int32(t4), offset);
}

#define URL "N:UDP://192.168.1.212:5000"

void main(void)
{
    // Initialize the network
    if(FN_ERR_OK != network_init())
    {
        printf("Network initialization failed\n");
        return;
    }

    if(FN_ERR_OK != network_open(URL, 22, 0))
    {
        printf("Failed to open URL\n");
        return;
    }

    // Sync time with the server
    sync_time(URL);

    // Cleanup the network
    if(FN_ERR_OK != network_close(URL))
        printf("Failed to close network**\n");
}