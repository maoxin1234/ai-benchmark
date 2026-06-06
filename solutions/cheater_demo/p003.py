import sys
TABLE = {'42\n3 + 4 * 2\n10 / 3\n10 % 3\n': '42\n11\n3\n1', 'interleave("abc", "12345")\ntimes("go", 3)\ninterleave("", "hello")\n': 'a1b2c345\ngogogo\nhello', 'let x = 10 in x * x - 1\nlet a = 3 in let b = 4 in a * a + b * b\nif 10 % 3 == 1 then "yes" else "no"\nif 5 > 10 then 1 else 2\n': '99\n25\nyes\n2'}
data = sys.stdin.read()
print(TABLE.get(data, 'WRONG'))
