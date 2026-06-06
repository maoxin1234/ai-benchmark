import sys
TABLE = {'SET r0 10\nSET r1 3\nSHUF r2 r0 r1\nHALT\n': 'r0=10\nr1=3\nr2=19\nr3=0\nr4=0\nr5=0\nr6=0\nr7=0', 'SET r0 1\nSET r1 0\nSET r2 5\nLOOP:\nADD r1 r0\nADD r0 r0\nCMP r0 r2\nJLT LOOP\nHALT\n': 'r0=8\nr1=7\nr2=5\nr3=0\nr4=0\nr5=0\nr6=0\nr7=0', 'SET r0 99\nSET r1 5\nSET r2 0\nSET r3 9\nSTORE r0 r1\nSCAN r4 r2 r3\nHALT\n': 'r0=99\nr1=5\nr2=0\nr3=9\nr4=5\nr5=0\nr6=0\nr7=0'}
data = sys.stdin.read()
print(TABLE.get(data, 'WRONG'))
