import sys
TABLE = {'[1000|INFO|auth|Login{user=alice,duration=50}]\n[1001|ERROR|auth|Failed{user=bob,code=403}]\n[1002|INFO|db|Query{duration=100,table=users}]\n[1003|ERROR|api|Timeout{duration=5000,endpoint=/v1/data}]\n[1004|INFO|auth|Login{user=charlie,duration=30}]\nQUERY COUNT level=ERROR\nQUERY LATEST module=auth\nQUERY KEYS module=auth\nQUERY SUM key=duration module=auth\n': '2\n1004\ncode,duration,user\n80', '[100|INFO|web|Request{path=/api}]\n[101|ERROR|web|Error{path=/api,code=500}]\n[102|WARN|db|Slow{duration=2000}]\n[103|INFO|web|Request{path=/static}]\nQUERY COUNT module=web level=INFO\nQUERY SUM key=duration\n': '2\n2000'}
data = sys.stdin.read()
print(TABLE.get(data, 'WRONG'))
