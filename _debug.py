# UI debug printing
import timeit

print('opening debug file!')

debug_file = open('debug.log', 'w+')
def debug_print(*args):
    strs = [str(x) for x in args]
    debug_file.write(' '.join(strs) + '\n')
    debug_file.flush()

print = debug_print

start_times = list() # stack
def st():
    global start_times
    start_times.append(timeit.default_timer())

def end(name):
    global start_times
    elapsed_time = timeit.default_timer() - start_times.pop()
    if elapsed_time > 5:
        print('\n')
    print('{:20} {:10.2f} ms'.format(name, elapsed_time * 1000))
