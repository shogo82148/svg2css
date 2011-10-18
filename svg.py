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
		elif name=="g":
			g = Group(attrs, self.__container)
			self.__container.append(g)
			self.__container = g
			assert g.parent
			
	def endElement(self, name):
		if name=="g":
			self.__container = self.__container.parent
			assert self.__container
		
	def getSVG(self):
		return self.__svg

#SVGの要素を表すクラス
class Element:
	def __init__(self, attrs, parent=None):
		self._parent = parent
		self.id = attrs.get("id", "")
		if attrs.has_key("transform"):
			self.transform = Transform(attrs.get("transform", ""))
		else:
			self.transform = None
	
	def callHandler(self, handler):
		pass
	
	@apply
	def parent():
		def get(self):
			return self._parent
		def set(self, p):
			self._parent = p
	
	def getElementById(self, id):
		if self.id==id:
			return self
		else:
			return None

#他のSVG要素を格納できるコンテナ
class Container(Element,list):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		list.__init__(self)
		self.__childids = {}
		
	def append(self, x):
		list.append(self, x)
		x.parent = self
		
	def extend(self, L):
		list.extend(self, L)
		for x in L:
			x.parent = self
	
	def insert(self, i, x):
		list.insert(self, i, x)
		x.parent = self

	def remove(self, x):
		list.remove(self, x)
		x.parent = None
	
	def pop(self, i=-1):
		list.pop(self, i)
		x.parent = None
		
	def getElementById(self, id):
		if self.id==id:
			return self
		for e in self:
			res = e.getElementById(id)
			if res:
				return res
		return None

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

#グループ
class Group(Container):
	def __init__(self, attrs, parent=None):
		Container.__init__(self, attrs, parent)
		
	def callHandler(self, handler):
		handler.group(self)

#SVG内での長さを表すクラス
class Length:
	__length_re = re.compile(r"^(?P<length>[+\-0-9e.]*)(?P<unit>[%a-z]*)$")
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
		return "%.2f%s" % (self.__length, self.__unit)
	
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
		
	def __neg__(a):
		return Length(-a.__length, a.__unit)
	
	def __pos__(a):
		return a;
	
	def __abs__(a):
		return Length(abs(a.__length), a.__unit)
	
	def __float__(a):
		return a.px


#スタイル
class Style(dict):
	def __init__(self, style=""):
		for item in style.split(";"):
			a = item.split(":")
			if len(a)<2: continue
			self[a[0]] = a[1]

#変形
class Transform(list):
	class BaseTransform:
		def toMatrix(self):
			raise

	class Translate(BaseTransform):
		def __init__(self, x, y= "0"):
			self.x = Length(x)
			self.y = Length(y)
		
		def __str__(self):
			return "translate(%s,%s)" % (str(self.x), str(self.y))
		
		def __mul__(self, a):
			if isinstance(a, Point):
				return Point(a.x+self.x, a.y+self.y)
			elif isinstance(a, Transform.Translate):
				return Transform.Translate(a.x+self.x, a.y+self.y)
			elif isinstance(a, Transform.BaseTransform):
				m = a.toMatrix()
				return Transform.Matrix(m.a, m.b, m.c, m.d, m.e+self.x.px, m.f+self.y.px)
			else:
				raise
		
		def toMatrix(self):
			return Transform.Matrix(1,0,0,1,self.x,self.y)

	class Matrix(BaseTransform):
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
				return Point(
					self.a*a.x+self.c*a.y+self.e,
					self.b*a.x+self.d*a.y+self.f)
			elif isinstance(a, Transform.BaseTransform):
				m = a.toMatrix()
				return Transform.Matrix(self.a*m.a+self.c*m.b,
					self.b*m.a+self.d*m.b,
					self.a*m.c+self.c*m.d,
					self.b*m.c+self.d*m.d,
					self.a*m.e+self.c*m.f+self.e,
					self.b*m.e+self.d*m.f+self.f)
			else:
				raise
		
		def toMatrix(self):
			return self
		
		def toStringMoz(self):
			return "matrix(%f,%f,%f,%f,%fpx,%fpx)" % (
				self.a, self.b, self.c, self.d,
				self.e, self.f)
		
	__filter_re = re.compile(r"(?P<name>[a-z]+)\((?P<args>[e+\-0-9,.]*)\)", re.I)
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
		
	def toMatrix(self):
		ret = Transform.Matrix(1,0,0,1,0,0)
		for m in self:
			ret = m * ret
		return ret

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
	
	def group(self, x):
		for a in x:
			a.callHandler(self)
	
	def rect(self, x):
		pass
	
	def arc(self, x):
		pass

class Color:
	__re_hex = re.compile("^#([0-9a-f][0-9a-f])([0-9a-f][0-9a-f])([0-9a-f][0-9a-f])$", re.I)
	def __init__(self, *larg, **darg):
		if len(larg)==1:
			#文字列
			m = Color.__re_hex.match(larg[0])
			if m:
				self.r = int(m.group(1), 16)
				self.g = int(m.group(2), 16)
				self.b = int(m.group(3), 16)
				self.a = 1.0
				return
			raise
		elif len(larg)==3:
			#(r,g,b)
			self.r = int(larg[0])
			self.g = int(larg[1])
			self.b = int(larg[2])
			self.a = 1.0
		elif len(larg)==4:
			#(r,g,b,a)
			self.r = int(larg[0])
			self.g = int(larg[1])
			self.b = int(larg[2])
			self.a = float(larg[3])
		else:
			self.r = int(darg.get("r", "0"))
			self.g = int(darg.get("g", "0"))
			self.b = int(darg.get("b", "0"))
			self.a = float(darg.get("a", "1"))

	def toHex(self):
		return "#%02x%02x%02x" % (self.r, self.g, self.b)
	
	def toRGB(self):
		return "rgb(%d,%d,%d)" % (self.r, self.g, self.b)
		
	def toRGBA(self):
		return "rgba(%d,%d,%d,%f)" % (self.r, self.g, self.b, self.a)

def main():
	filename = sys.argv[1]
	p = Parser()
	p.parse(open(filename, "r"))
	return

if __name__=="__main__":
	main()
