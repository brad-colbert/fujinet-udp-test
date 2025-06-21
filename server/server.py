import socket
import json
import time
from random import random
import struct
import binascii

# Server settings
HOST = "" #127.0.0.1"
PORT = 5000
BUFFER_SIZE = 1024
start_time = None

# Packet format: [type, client_id, x, y, sequence, timestamp]
'''
typedef struct _entity {
    int16_t x, y;
    int16_t vx, vy;   // velocity in pixel/second (1 second is 60 frames NTSC, 50 frames PAL)
} Entity;
typedef struct _sim_packet {
    uint8_t t_ms[4];
    uint16_t sequence;
    uint8_t msg_type;
    uint8_t padding;
    Entity entity;
} SimPacket;
'''
header_unpacker = struct.Struct('I H B')
entity_unpacker = struct.Struct('I H B B h h h h')

# Player data storage (player_id -> position, timestamp, last_seq)
player_data = {}

# Create UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((HOST, PORT))

print(f"Enhanced UDP MMO Server running on {HOST}:{PORT}")

def interpolate_position(old_pos, new_pos, alpha=0.9):
    """Interpolates between two positions for smoother movement."""
    return {
        "x": old_pos["x"] * (1 - alpha) + new_pos["x"] * alpha,
        "y": old_pos["y"] * (1 - alpha) + new_pos["y"] * alpha
    }

def get_time():
    global start_time
    if start_time is None:
        start_time = time.time()
    return time.time() - start_time

def fixed_point_to_float(fixed_point: int) -> float:
    """Converts a 16-bit signed fixed point number to a floating point number."""
    # Handle two's complement for negative values
    sign = 1
    if fixed_point & 0x8000:
        sign = -1
        fixed_point = ~(fixed_point-1)#-((~fixed_point & 0xFFFF) + 1)
    # Extract the 12-bit whole number part
    whole_number = (fixed_point >> 4) & 0xFFF
    # Extract the 4-bit fraction part
    fraction = fixed_point & 0xF
    # Combine the whole number and fraction
    return sign * (whole_number + (fraction / 16.0))

def float_to_fixed_point(value: float) -> int:
    """Converts a floating point number to a 16-bit signed fixed point number."""
    sign = 1
    if value < 0:
        sign = -1
        value = abs(value)
    whole_number = int(value)
    fraction = int((value - whole_number) * 16)
    fixed_point = (whole_number << 4) | (fraction & 0xF)
    if sign == -1:
        fixed_point = -fixed_point
    return fixed_point & 0xFFFF

real_start_time = loop_start = time.time()

# **NOTE** All time is in milliseconds
print("Starting at", get_time())
while True:
    try:
        '''
        '''
        # Keep track of time
        now = get_time()

        # Receive data from a client
        data, addr = server_socket.recvfrom(BUFFER_SIZE)

        data_size = len(data)
        player_id = str(addr)  # Unique ID based on client address

        print(f"{data_size}:data:", binascii.hexlify(data), end=' ')

        # Just header (probably time sync)
        if 7 == data_size:
            unpacked_data = header_unpacker.unpack(data)
        # Entity packet
        elif 16 == data_size:
            unpacked_data = entity_unpacker.unpack(data)

        print(unpacked_data, end=' ')

        packet_header = { "t_ms": unpacked_data[0],
                          "sequence": unpacked_data[1],
                          "msg_type": unpacked_data[2],
                        }
        
        print(packet_header)
        
        timestamp = packet_header["t_ms"] / 1000.0  # Convert milliseconds to seconds


        if packet_header["msg_type"] == ord('t'):
            t2 = get_time()
            print(f"Time sync: {t2:.3f} ({timestamp:.3f}) ", end='')
            # Send back the time T2
            t2_ms = int(t2 * 1000.0)  # Convert seconds to milliseconds
            server_socket.sendto(struct.pack('I H B', t2_ms, 1, ord('t')), addr)
            print(f"{addr}|t2: 0x{t2_ms:08X} ", t2_ms, 1, ord('t'), end='  ')

            #time.sleep(1.0)

            # Send T3
            t3 = get_time()
            t3_ms = int(t3 * 1000.0) # Convert seconds to milliseconds
            server_socket.sendto(struct.pack('I H B', t3_ms, 2, ord('t')), addr)
            print(f"{addr}|t3: {t3:.3f} 0x{t3_ms:08X} (0x{packet_header['t_ms']:08X})", t3_ms, 2, ord('t'))

        elif packet_header["msg_type"] == ord('m'):    # Movement
            sim_packet = { "header": packet_header,
                           "entity": {"x": (unpacked_data[4]),
                                      "y": (unpacked_data[5]),
                                      "vx": (unpacked_data[6]),
                                      "vy": (unpacked_data[7])} }            
            
            print(f'Data {player_id}: {sim_packet["entity"]["x"]},{sim_packet["entity"]["y"]} - {sim_packet["entity"]["vx"]},{sim_packet["entity"]["vy"]} {(now - timestamp)}')
            '''
                           "entity": {"x": fixed_point_to_float(unpacked_data[4]),
                                      "y": fixed_point_to_float(unpacked_data[5]),
                                      "vx": fixed_point_to_float(unpacked_data[6]),
                                      "vy": fixed_point_to_float(unpacked_data[7])} }            
            
            print(f'Data {player_id}: {sim_packet["entity"]["x"]:.1f},{sim_packet["entity"]["y"]:.1f} - {sim_packet["entity"]["vx"]:.1f},{sim_packet["entity"]["vy"]:.1f} {(now - timestamp):.3f}')
            '''

            sequence = sim_packet["header"]["sequence"]

            # Initialize player if first time
            if player_id not in player_data:
                player_data[player_id] = {"x": sim_packet["entity"]["x"], "y": sim_packet["entity"]["y"], "last_seq": -1, "last_time": timestamp}

            # Ignore old/out-of-order packets
            if sequence <= player_data[player_id]["last_seq"]:
                continue

            # Estimate player's real position using lag compensation
            ping_time = get_time() - timestamp
            estimated_x = sim_packet["entity"]["x"] + ping_time * sim_packet["entity"]["vx"]  # pix/sec
            estimated_y = sim_packet["entity"]["y"] + ping_time * sim_packet["entity"]["vy"]
            print(f"Estimate {player_id}: {estimated_x:.1f},{estimated_y:.1f}")

            # Interpolate between previous and estimated position
            smooth_pos = interpolate_position(player_data[player_id], {"x": estimated_x, "y": estimated_y})

            # Update player position
            player_data[player_id]["x"] = smooth_pos["x"]
            player_data[player_id]["y"] = smooth_pos["y"]
            player_data[player_id]["last_seq"] = sequence
            player_data[player_id]["last_time"] = timestamp
            print(f"Smoothed {player_id}: {smooth_pos['x']:.1f},{smooth_pos['y']:.1f}")
            print(f"T: {int(timestamp*1000.0):08X} S: {sequence:04X} X: {int(smooth_pos['x']):04x}, Y: {int(smooth_pos['y']):04x}")

            # Broadcast new positions to all players
            '''
            '''
            try:
                for client_addr in player_data.keys():
                    update_date = struct.pack('I h h h', int(timestamp*1000.0), sequence, int(smooth_pos['x']), int(smooth_pos['y']))
                    server_socket.sendto(update_date, eval(client_addr))
                    print('{!r}'.format(binascii.hexlify(update_date)))
            except Exception as e:
                print(f"Error: {e}")

        '''
        # Receive data from a client
        data, addr = server_socket.recvfrom(BUFFER_SIZE)

        unpacked_data = unpacker.unpack(data)
        sim_packet = { "rtclock": unpacked_data[0],
                       "sequence": unpacked_data[1],
                       "msg_type": unpacked_data[2],
                       "ntsc_flag": unpacked_data[3],
                       "entity": {"x": fixed_point_to_float(unpacked_data[4]),
                                  "y": fixed_point_to_float(unpacked_data[5]),
                                  "vx": fixed_point_to_float(unpacked_data[6]),
                                  "vy": fixed_point_to_float(unpacked_data[7])} }            
        client_time = sim_packet["rtclock"]

        # Have to correct time to be in line with the rtclock on the atari
        now = time.time()
        if start_time is None:
            start_time = time_jiffy(sim_packet["ntsc_flag"]) - client_time
        timestamp = time_jiffy(sim_packet["ntsc_flag"]) - start_time
        drift = timestamp - client_time  # in jiffys
        drift_t = drift/((now - real_start_time)/60.0)   # jiffy's per minute

        delta_time = now - loop_start
        loop_start = now
        print('{!r}'.format(binascii.hexlify(data)) + f' {sim_packet["rtclock"]}, {sim_packet["sequence"]}, drift:{drift} drift_t:{drift_t:.3f} d:{delta_time:.3f} t:{now - real_start_time:.3f}', )
        print(f'position: {sim_packet["entity"]["x"]},{sim_packet["entity"]["y"]}',
              f'velocity: {sim_packet["entity"]["vx"]},{sim_packet["entity"]["vy"]}')
        '''


        # send back the time
        #update_time = timestamp
        #packed_data = unpacker.pack(update_time, unpacked_data[1])
        #server_socket.sendto(packed_data, addr)

    except Exception as e:
        print(f"Error: {e}")