#!/usr/bin/python
import readline
from parser import parse

def main():
	try:
		while(True):
			evalexpr(input())
	except EOFError:
		pass
def evalexpr(expr):
	parsedexpr = parse(expr)
	print(parsedexpr.eval())

if __name__=='__main__':
	main()

