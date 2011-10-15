# -*- coding:utf-8 -*-

import xml.sax
import xml.sax.handler
import sys
import re
from collections import namedtuple

class Parser:
	def __init__(self):
		self.__parser = xml.sax.make_parser()
		self.__handler = SVGXMLHandler()
		self.__parser.setContentHandler(self.__handler)
		self.__parser.setFeature(xml.sax.handler.feature_external_ges, False)
	
	def parse(self, data):
		self.__parser.parse(data)
		return self.__handler.getSVG()
	

class SVGXMLHandler(xml.sax.handler.ContentHandler):
	def __init__(self):
		self.__container = None
		self.__svg = None
		
	def startElement(self, name, attrs):
		type = attrs.get('sodipodi:type', '')
		if type=="arc":
			self.__container.append(Arc(attrs))
		elif name=="svg":
			self.__container = SVG(attrs, self.__container)
			self.__svg = self.__container
		elif name=="rect":
			self.__container.append(Rect(attrs))
			
	def endElement(self, name):
		pass
		
	def getSVG(self):
		return self.__svg

#SVGの要素を表すクラス
class Element:
	def __init__(self, attrs, parent=None):
		self.__parent = parent
		self.id = attrs.get("id", "")
		if attrs.has_key("transform"):
			self.transform = Transform(attrs.get("transform", ""))
		else:
			self.transform = None
	
	def callHandler(self, handler):
		pass
	
	@apply
	def parrent():
		def get(self):
			return self.__parent

#他のSVG要素を格納できるコンテナ
class Container(Element,list):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		list.__init__(self)
		
	def append(self, x):
		list.append(self, x)
		x._Element__parent = self
		
	def extend(self, L):
		list.extend(self, L)
		for x in L:
			x._Element__parent = self
	
	def insert(self, i, x):
		list.insert(self, i, x)
		x._Element__parent = self

	def remove(self, x):
		list.remove(self, x)
		x._Element__parent = None
	
	def pop(self, i=-1):
		list.pop(self, i)
		x._Element__parent = None

#SVG画像
class SVG(Container):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		self.x = Length(attrs.get("x", "0"))
		self.y = Length(attrs.get("y", "0"))
		self.width = Length(attrs.get("width", "0"))
		self.height = Length(attrs.get("height", "0"))
		
	def callHandler(self, handler):
		handler.svg(self)

#長方形
class Rect(Element):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		self.x = Length(attrs.get("x", "0"))
		self.y = Length(attrs.get("y", "0"))
		self.width = Length(attrs.get("width", "0"))
		self.height = Length(attrs.get("height", "0"))
		self.rx = Length(attrs["rx"]) if attrs.has_key("rx") else None
		self.ry = Length(attrs["ry"]) if attrs.has_key("ry") else None
		self.style = Style(attrs.get("style", ""))
		
	def callHandler(self, handler):
		handler.rect(self)

#円弧
class Arc(Element):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		self.cx = Length(attrs.get("sodipodi:cx", "0"))
		self.cy = Length(attrs.get("sodipodi:cy", "0"))
		self.rx = Length(attrs.get("sodipodi:rx", "0"))
		self.ry = Length(attrs.get("sodipodi:ry", "0"))
		self.style = Style(attrs.get("style", ""))
		
	def callHandler(self, handler):
		handler.arc(self)

#SVG内での長さを表すクラス
class Length:
	__length_re = re.compile(r"(?P<length>[+\-0-9.]*)(?P<unit>[%a-z]*)")
	__px_per_unit = {
		"px": 1.0,
		"in": 90.0,
		"mm": 90.0/25.4,
		"cm": 90.0/2.54,
	}
	
	def __init__(self, length, unit = None):
		if unit:
			self.__length = float(length)
			self.__unit = unit
		else:
			m = Length.__length_re.match(str(length))
			if not m: raise
			self.__length = float(m.group('length'))
			self.__unit = m.group('unit') or "px"
	
	@property
	def px(self):
		return self.__length * Length.__px_per_unit[self.__unit]
	
	def __str__(self):
		return str(self.__length) + self.__unit
	
	def __add__(a, b):
		if isinstance(b, Length):
			return Length(a.px + b.px, "px")
		else:
			return Length(a.px + b, "px")
	
	def __sub__(a, b):
		if isinstance(b, Length):
			return Length(a.px - b.px, "px")
		else:
			return Length(a.px - b, "px")
	
	def __mul__(a, b):
		return Length(a.__length * b, a.__unit)
	
	def __rmul__(a, b):
		return Length(a.__length * b, a.__unit)
	
	def __div__(a, b):
		return Length(a.__length / b, a.__unit)

#スタイル
class Style(dict):
	def __init__(self, style=""):
		for item in style.split(";"):
			a = item.split(":")
			if len(a)<2: continue
			self[a[0]] = a[1]

#変形
class Transform(list):
	class Translate:
		def __init__(self, x, y= "0"):
			self.x = Length(x)
			self.y = Length(y)
		

		def __str__(self):
			return "translate(%s,%s)" % (str(self.x), str(self.y))

	class Matrix:
		def __init__(self, a, b, c, d, e, f):
			self.a = float(a)
			self.b = float(b)
			self.c = float(c)
			self.d = float(d)
			self.e = float(e)
			self.f = float(f)
		
		def __str__(self):
			return "matrix(%f,%f,%f,%f,%f,%f)" % (
				self.a, self.b, self.c, self.d,
				self.e, self.f)
				
		def __mul__(self, a):
			if isinstance(a, Point):
				print str(self)
				return Point(
					self.a*a.x+self.c*a.y,
					self.b*a.x+self.d*a.y)
			elif isinstance(a, Translate):
				raise
			else:
				raise
		
	__filter_re = re.compile(r"(?P<name>[a-z]+)\((?P<args>[\-0-9,.]*)\)", re.I)
	__transforms_dict = {
		"translate": Translate,
		"matrix": Matrix,
	}
	def __init__(self, s):
		list.__init__(self)
		s = s.replace(" ", "").replace("\t", "")
		for m in Transform.__filter_re.finditer(s):
			name = m.group("name")
			args = m.group("args").split(",")
			transform = Transform.__transforms_dict[name](*args)
			self.append(transform)
		
	def __str__(self):
		return " ".join([str(f) for f in self])

class Point(namedtuple('Point', 'x y')):
	__slots__ = ()
	
	def __add__(a, b):
		return Point(a.x+b.x, a.y+b.y)
	
	def __sub__(a, b):
		return Point(a.x-b.x, a.y-b.y)

class SVGHandler:
	def svg(self, x):
		for a in x:
			a.callHandler(self)
			
	def rect(self, x):
		pass
	
	def arc(self, x):
		pass

def main():
	filename = sys.argv[1]
	p = Parser()
	p.parse(open(filename, "r"))
	return

if __name__=="__main__":
	main()
