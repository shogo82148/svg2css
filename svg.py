# -*- coding:utf-8 -*-

import xml.sax
import xml.sax.handler
import sys
import re
from collections import namedtuple
import math

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
			self.__container = SVG(attrs)
			self.__svg = self.__container
		elif name=="rect":
			self.__container.append(Rect(attrs))
		elif name=="g":
			g = Group(attrs)
			self.__container.append(g)
			self.__container = g
			assert g.parent
		elif name=="defs":
			g = Define(attrs)
			self.__container.append(g)
			self.__container = g
			assert g.parent
		elif name=="linearGradient":
			g = LinearGradient(attrs)
			self.__container.append(g)
			self.__container = g
			assert g.parent
		elif name=="radialGradient":
			g = RadialGradient(attrs)
			self.__container.append(g)
			self.__container = g
			assert g.parent
		elif name=="stop":
			self.__container.append(Stop(attrs))
		elif name=="use":
			self.__container.append(Use(attrs))
		elif name=="clipPath":
			g = ClipPath(attrs)
			self.__container.append(g)
			self.__container = g
			assert g.parent
			
	def endElement(self, name):
		if name=="g":
			self.__container = self.__container.parent
			assert self.__container
		elif name=="defs":
			self.__container = self.__container.parent
			assert self.__container
		elif name=="linearGradient":
			self.__container = self.__container.parent
			assert self.__container
		elif name=="radialGradient":
			self.__container = self.__container.parent
			assert self.__container
		elif name=="clipPath":
			self.__container = self.__container.parent
			assert self.__container
		
	def getSVG(self):
		return self.__svg

#SVGの要素を表すクラス
class Element:
	__all_defalut = {
		"transform": None,
	}
	def __init__(self, attrs, parent=None, default={}):
		self.__parent = parent
		self.__default = default
		self.__root = None
		self.id = attrs.get("id", "")
		
		self.transform = Transform(attrs.get("transform", ""))
		
		if attrs.has_key("xlink:href"):
			self.href = attrs.get("xlink:href")
		else:
			self.href = None
			
	def callHandler(self, handler):
		pass
	
	@property
	def parent(self):
		return self.__parent

	@parent.setter
	def parent(self, p):
		self.__parent = p
		self.__root = None

	@property
	def root(self):
		#if not self.__root:
		if self.parent:
			self.__root = self.parent.root
		else:
			self.__root = self
		return self.__root
	
	def getElementById(self, id):
		if self.id==id:
			return self
		return None

#他のSVG要素を格納できるコンテナ
class Container(Element,list):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		list.__init__(self)
		self.__childids = {}
		
	def append(self, x):
		list.append(self, x)
		self.__appendChild(x)
		
	def extend(self, L):
		list.extend(self, L)
		for x in L:
			self.__appendChild(x)
	
	def insert(self, i, x):
		list.insert(self, i, x)
		self.__appendChild(x)

	def remove(self, x):
		list.remove(self, x)
		self.__removeChild(x)
	
	def pop(self, i=-1):
		x = list.pop(self, i)
		self.__removeChild(x)
		return x
	
	def __removeChild(self, x):
		x.parent = None
		self.__removeId(x)
		
	def __appendChild(self, x):
		parent = x.parent
		if parent==self:
			return
		if parent:
			index = parent.index(x)
			parent.remove(index)
		x.parent = self
		self.__appendId(x)
	
	def __removeId(self, x):
		if x.id:
			del self.__childids[x.id]
		if isinstance(x, Container):
			for id,child in x.__childids.iteritems():
				del self.__childids[id]
		if self.parent:
			self.parent.__removeId(x)
	
	def __appendId(self, x):
		id = x.id
		if id:
			self.__childids[id] = x
		if isinstance(x, Container):
			for id,child in x.__childids.iteritems():
				self.__childids[id] = child
		if self.parent:
			self.parent.__appendId(x)
	
	def getElementById(self, id):
		if self.id==id:
			return self
		return self.__childids.get(id, None)

#SVG画像
class SVG(Container):
	def __init__(self, attrs, parent=None):
		Container.__init__(self, attrs, parent)
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
		self.clip_path = attrs.get("clip-path", "")
		
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
		self.clip_path = attrs.get("clip-path", "")
		
	def callHandler(self, handler):
		handler.arc(self)

#グループ
class Group(Container):
	def __init__(self, attrs, parent=None):
		Container.__init__(self, attrs, parent)
		
	def callHandler(self, handler):
		handler.group(self)

#defタグ
class Define(Container):
	def __init__(self, attrs, parent=None):
		Container.__init__(self, attrs, parent)
		
	def callHandler(self, handler):
		handler.define(self)

#線形グラデーション
class LinearGradient(Container):
	def __init__(self, attrs, parent=None):
		Container.__init__(self, attrs, parent)
		self.x1 = Length(attrs.get("x1", "0"))
		self.y1 = Length(attrs.get("y1", "0"))
		self.x2 = Length(attrs.get("x2", "0"))
		self.y2 = Length(attrs.get("y2", "0"))
		self.gradientUnits = attrs.get("gradientUnits", "objectBoundingBox")
		self.gradientTransform = Transform(attrs.get("gradientTransform", ""))
		
	def callHandler(self, handler):
		handler.linearGradient(self)

#円形グラデーション
class RadialGradient(Container):
	def __init__(self, attrs, parent=None):
		Container.__init__(self, attrs, parent)
		self.cx = Length(attrs.get("cx", "0"))
		self.cy = Length(attrs.get("cy", "0"))
		self.fx = Length(attrs.get("fx", "0"))
		self.fy = Length(attrs.get("fy", "0"))
		self.r = Length(attrs.get("r", "0"))
		self.gradientUnits = attrs.get("gradientUnits", "objectBoundingBox")
		self.gradientTransform = Transform(attrs.get("gradientTransform", ""))
		
	def callHandler(self, handler):
		handler.radialGradient(self)

#グラデーションの色指定
class Stop(Element):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		self.offset = float(attrs.get("offset", "0"))
		self.style = Style(attrs.get("style", ""))
	
	def callHandler(self, handler):
		handler.use(self)

class ClipPath(Container):
	def __init__(self, attrs, parent=None):
		Container.__init__(self, attrs, parent)
		self.gradientUnits = attrs.get("clipPathUnits", "objectBoundingBox")
		
	def callHandler(self, handler):
		handler.clipPath(self)

class Use(Element):
	def __init__(self, attrs, parent=None):
		Element.__init__(self, attrs, parent)
		self.x = Length(attrs.get("x", "0"))
		self.y = Length(attrs.get("y", "0"))
		self.width = Length(attrs.get("width", "0"))
		self.height = Length(attrs.get("height", "0"))
	
	def callHandler(self, handler):
		handler.use(self)

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
		elif isinstance(length, Length):
			self.__length = length.__length
			self.__unit = length.__unit
		else:
			m = Length.__length_re.match(str(length))
			if not m: raise
			self.__length = float(m.group('length'))
			self.__unit = m.group('unit') or "px"
	
	@property
	def px(self):
		return self.__length * Length.__px_per_unit[self.__unit]
		
	def __repr__(self):
		return "%.2f%s" % (self.__length, self.__unit)
		
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
		if isinstance(b, Length):
			return a.px/b.px
		else:
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
		
		def inverse(self):
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
		
		def inverse(self):
			return Transform.Translate(-self.x, -self.y)

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
		
		def inverse(self):
			det = self.a*self.d-self.b*self.c
			return Transform.Matrix(self.d/det, -self.b/det, -self.c/det, self.a/det,0,0) * Transform.Translate(-self.e, -self.f)
			
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
	
	def __mul__(a, b):
		if isinstance(b, Point):
			return a.x*b.x+a.y*b.y
		else:
			return Point(a.x*b, a.y*b)

	def __div__(a, b):
		return Point(a.x/b, a.y/b)
		
	def __abs__(self):
		return math.sqrt(self.x.px*self.x.px + self.y.px*self.y.px)
		
class SVGHandler:
	def svg(self, x):
		for a in x:
			a.callHandler(self)
	
	def group(self, x):
		for a in x:
			a.callHandler(self)
	
	def define(self, x):
		pass
	
	def linearGradient(self, x):
		pass

	def radialGradient(self, x):
		pass
	
	def clipPath(self, x):
		pass
	
	def use(self, x):
		x.root.getElementById(x.href[1:]).callHandler(self)
	
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
	
	@classmethod
	def gradient(cls, a, b, offset):
		ioffset = 1 - offset
		return Color(
			ioffset*a.r + offset*b.r,
			ioffset*a.g + offset*b.g,
			ioffset*a.b + offset*b.b,
			ioffset*a.a + offset*b.a)
			
	def __repr__(self):
		if self.a>0.999:
			return self.toHex()
		else:
			return self.toRGBA()

	def __str__(self):
		if self.a>0.999:
			return self.toHex()
		else:
			return self.toRGBA()

def main():
	m = Transform.Matrix(1,2,3,4,5,6)
	print m
	print m.inverse()
	print m*m.inverse()
	return

if __name__=="__main__":
	main()
