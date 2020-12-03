#!/usr/bin/python
import readline
from parser import parse
from lark import ParseError

def main():
	try:
		while(True):
			curr_expr = []
			while(True):
				try:
					curr_expr.append(input())
					evalexpr("\n".join(curr_expr))
				except ParseError:
					continue
				break
	except EOFError:
		pass
def evalexpr(expr):
	parsedexpr = parse(expr)
	print(parsedexpr.eval())

if __name__=='__main__':
	main()

