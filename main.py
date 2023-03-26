import json
import ntptime
from machine import Timer
from writer import Writer
from centerwriter import CenterWriter
from fonts import jetbrains35, freesans20
from drivers import epd_2in9
import network
import utime
import time

MONTHS_IN_DUTCH = ['januari', 'februari', 'maart', 'april', 'mei', 'juni',
                   'juli', 'augustus', 'september', 'oktober', 'november', 'december']


def read_config_from_json():
    with open('config.json', 'r') as f:
        return json.load(f)


config = read_config_from_json()


def connect_to_network():
    ssid = config["wifi_ssid"]
    password = config['wifi_password']
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    # Wait for connect or fail
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        time.sleep(1)

        # Handle connection error
    if wlan.status() != 3:
        print('network connection failed skipping ntp check')
        return None
    else:
        status = wlan.ifconfig()
        return wlan


def sync_ntp():
    print("Starting NTP sync")
    print("Local time before synchronization：%s" % str(time.localtime()))
    wn = connect_to_network()
    if wn is None:
        print("Network connection failed skipping ntp check")
        return

    ntptime.settime()
    print("Local time after synchronization：%s" % str(time.localtime()))
    wn.disconnect()


TZ_OFFSET = 3600 * 2  # 2 HOURS


def format_time_to_military(local_time_with_tz) -> str:
    return "%02d:%02d" % (local_time_with_tz[3], local_time_with_tz[4])


def format_date_to_dutch(local_time_with_tz) -> str:
    return "%02d %s %d" % (local_time_with_tz[2], MONTHS_IN_DUTCH[local_time_with_tz[1] - 1], local_time_with_tz[0])


def get_local_time_with_tz():
    local_time_ts = utime.mktime(time.localtime()) + TZ_OFFSET
    return utime.localtime(local_time_ts)


print(format_time_to_military(get_local_time_with_tz()))

epd = epd_2in9.EPD_2in9_Landscape()
epd.fill(0xff)


cw = CenterWriter(epd, jetbrains35)
cw.set_vertical_spacing(10)
cw.set_horizontal_shift(90)
cw.set_vertical_shift(-96)

date_writer = CenterWriter(epd, freesans20)
date_writer.set_vertical_spacing(10)
date_writer.set_horizontal_shift(90)
date_writer.set_vertical_shift(-72)


def update_screen(time, date):
    cw.write_lines([time])
    date_writer.write_lines([date])
    epd.display(epd.buffer)


local_time = get_local_time_with_tz()
current_time = format_time_to_military(local_time)
current_date = format_date_to_dutch(local_time)
update_screen(current_time, current_date)


def update_clock():
    global current_time

    local_time = get_local_time_with_tz()
    new_time = format_time_to_military(local_time)
    if new_time != current_time:
        update_screen(new_time, format_date_to_dutch(local_time))

    current_time = new_time


if __name__ == '__main__':
    SECOND = 1000
    timer = Timer(-1)
    timer.init(period=SECOND, mode=Timer.PERIODIC,
               callback=lambda t: update_clock())

    # hardware timer for ntp sync every hour
    sync_ntp()
    sync_ntp_timer = Timer(-1)
    sync_ntp_timer = sync_ntp_timer.init(period=60 * 60 * SECOND, mode=Timer.PERIODIC,
                                         callback=lambda t: sync_ntp())
