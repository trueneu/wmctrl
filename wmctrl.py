#!/usr/bin/env python3

# todo: upload to github

import os
import signal
import subprocess
import shlex
import pickle
import sys
from collections import deque

STATE_PATH = os.environ["HOME"] + '/.wmctrl.state'
DEQUE_KEY = "deque"
SET_KEY = "set"
state = {}
DEBUG = 0

def save_state():
    with open(STATE_PATH, 'wb') as f:
        pickle.dump(state, f)


def load_state():
    global state
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, 'rb') as f:
            state = pickle.load(f)


def get_windows(window_filter):
    if not window_filter:
        return
    p1 = subprocess.Popen(shlex.split('wmctrl -l -x'), stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split('fgrep {}'.format(window_filter)), stdin=p1.stdout, stdout=subprocess.PIPE)
    output = p2.communicate()

    # todo: bad naming
    newset = set()
    # todo: feels a bit hacky
    window_class = ""
    for line in output[0].decode().split('\n'):
        parts = line.split()
        if len(parts) >= 5:
            DEBUG and print(parts)
            window_id, desktop_number, window_class, client_host, window_title = parts[0], parts[1], parts[2], parts[
                3], ' '.join(parts[4:])
            window_id = int(window_id, 16)
            DEBUG and print(window_class)
            newset.add(window_id)
            if window_class not in state:
                state[window_class] = {DEQUE_KEY: deque(), SET_KEY: set()}
            if window_id not in state[window_class][SET_KEY]:
                state[window_class][SET_KEY].add(window_id)
                state[window_class][DEQUE_KEY].append(window_id)
    for window_id in state[window_class][SET_KEY].difference(newset):
        state[window_class][SET_KEY].remove(window_id)

        # todo: maybe filter or something instead of iteration
        deletion_set = set()
        for idx, window_id_deque in enumerate(state[window_class][DEQUE_KEY]):
            if window_id_deque == window_id:
                deletion_set.add(idx)
        # todo: runtime complexity is certainly not the best
        for idx in deletion_set:
            del state[window_class][DEQUE_KEY][idx]


def start_program(program):
    signal.pthread_sigmask(signal.SIG_BLOCK, [signal.SIGCHLD])
    newpid = os.fork()
    if newpid == 0:
        os.setsid()
        newpid2 = os.fork()
        if newpid2 == 0:
            sys.stdout.flush()
            sys.stderr.flush()
            os.execve(program, [program], os.environ)
            sys.exit(0)
        else:
            sys.exit(0)
    else:
        signal.pthread_sigmask(signal.SIG_UNBLOCK, [signal.SIGCHLD])
        os.waitpid(newpid, 0)
        sys.exit(0)


def choose_window_id(f):
    if f not in state: return None
    window_id = state[f][DEQUE_KEY].popleft()
    state[f][DEQUE_KEY].append(window_id)
    return window_id


def switch_focus(window_id):
    cmd = 'wmctrl -i -a {}'.format(hex(window_id))
    subprocess.call(shlex.split(cmd))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(1)
    window_filter = sys.argv[1]
    load_state()
    get_windows(window_filter)
    wid = choose_window_id(window_filter)
    DEBUG and print("new wid " + str(wid))
    switch_focus(wid)
    save_state()
    DEBUG and print(state)
    # start_program('/usr/bin/uxterm')
    # switch_focus('0x00c0000f')
