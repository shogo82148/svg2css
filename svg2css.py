#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import svg

class CSSStyle(dict):
	def __str__(self):
		s = ""
		for name,style in self.iteritems():
			if name=="transform":
				s += CSSStyle.__transform(style)
				continue
			if not isinstance(style, str):
				style = str(style)
			s += "%s:%s;" % (name, style)
		return s
	
	@classmethod
	def __transform(cls, transform):
		style = str(transform)
		s = ""
		for name in ["transform", "-ms-transform", "-o-transform", "-webkit-transform"]:
			s += "%s:%s;" % (name, style)
		s += "-moz-transform:%s;" % transform.toStringMoz()
		return s
	
	def addFill(self, svgstyle):
		if "fill" not in svgstyle or svgstyle["fill"] == "none":
			return
			
		try:
			color = svg.Color(svgstyle["fill"])
			if "fill-opacity" in svgstyle:
				color.a = float(svgstyle["fill-opacity"])
			self["background-color"] = color
		except:
			pass
			
class CSSWriter(svg.SVGHandler):
	def __init__(self, name):
		self.__name = name
		self.__html = open(name + ".html", "w")
		self.__css = open(name + ".css", "w")
		self.__id = 0
		self.__css_classes = set()
		
	def newName(self, x=None):
		if x and isinstance(x, svg.Element) and x.id:
			return "svg" + x.id
		self.__id = self.__id + 1
		return "id%04d" % self.__id
		
	def svg(self, x):
		self.__html.write("""<!DOCTYPE html> 
<head> 
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta http-equiv="content-script-type" content="text/javascript" /> 
<meta http-equiv="content-style-type" content="text/css" /> 
<link rel="stylesheet" href="./%s.css">
</head>
<body>
<div class="svg">\n""" % self.__name)
		#self.__css.write('@charset "utf-8"\n\n.a{}\n')
		self.__css.write(".svg{top:0px;left:0px;width:%s;height:%s;position:absolute;}\n" % (str(x.width), str(x.height)))
		svg.SVGHandler.svg(self, x)
		self.__html.write("""</div>\n</body></html>\n""")
		
	def rect(self, x):
		name = self.newName(x)
		if name not in self.__css_classes:
			self.__css_classes.add(name)
			css = CSSStyle()
			stroke = svg.Length(0)
			
			#ストロークの描画
			if "stroke" in x.style and x.style["stroke"] != 'none':
				try:
					stroke = svg.Length(x.style.get("stroke-width",1))
					css["border-width"] = stroke
					css["border-style"] = "solid"
					color = svg.Color(x.style["stroke"])
					if "stroke-opacity" in x.style:
						color.a = float(x.style["stroke-opacity"])
					css["border-color"] = color
				except:
					pass
			
			#位置と大きさの設定
			css["position"] = "absolute"
			css["left"] = x.x - stroke/2
			css["top"] = x.y - stroke/2
			css["width"] = x.width - stroke
			css["height"] = x.height - stroke
			
			#角を丸める
			if x.rx and x.ry:
				css["border-radius"] = "%s/%s" % (str(x.rx+stroke/2), str(x.ry+stroke/2))
			elif x.rx:
				css["border-radius"] = x.rx+stroke/2
			elif x.ry:
				css["border-radius"] = x.ry+stroke/2
		
			#変形
			if x.transform:
				#CSSとSVGの原点の違いを補正
				transform = x.transform.toMatrix()
				transform = transform * svg.Transform.Translate(x.x+x.width/2, x.y+x.height/2)
				transform = svg.Transform.Translate(-x.x-x.width/2, -x.y-x.height/2) * transform
				css["transform"] = transform

			#フィルを指定する
			css.addFill(x.style)
				
			#出力
			self.__css.write(".%s{%s}\n" % (name, str(css)))
			
		self.__html.write('<div class="%s"></div>\n' % name)
	
	def arc(self, x):
		name = self.newName(x)
		if name not in self.__css_classes:
			self.__css_classes.add(name)
			css = CSSStyle()
			stroke = svg.Length(0)
			
			#ストロークの描画
			if "stroke" in x.style and x.style["stroke"] != 'none':
				try:
					stroke = svg.Length(x.style.get("stroke-width",1))
					css["border-width"] = stroke
					css["border-style"] = "solid"
					color = svg.Color(x.style["stroke"])
					if "stroke-opacity" in x.style:
						color.a = float(x.style["stroke-opacity"])
					css["border-color"] = color
				except:
					pass
					
			#位置と大きさの設定
			css["position"] = "absolute"
			css["left"] = str(x.cx - x.rx - stroke/2)
			css["top"] = str(x.cy - x.ry - stroke/2)
			css["width"] = str(x.rx * 2 - stroke)
			css["height"] = str(x.ry * 2 - stroke)
			
			#角を丸める
			css["border-radius"] = "%s/%s" % (str(x.rx+stroke/2), str(x.ry+stroke/2))
		
			#フィルを指定する
			css.addFill(x.style)
			
			#変形
			if x.transform:
				#CSSとSVGの原点の違いを補正
				transform = x.transform.toMatrix()
				transform = transform * svg.Transform.Translate(x.cx, x.cy)
				transform = svg.Transform.Translate(-x.cx, -x.cy) * transform
				css["transform"] = transform
			
			#出力
			self.__css.write(".%s{%s}\n" % (name, str(css)));
		self.__html.write('<div class="%s"></div>\n' % name);
	
	def group(self, x):
		name = self.newName(x)
		if name not in self.__css_classes:
			self.__css_classes.add(name)
			css = CSSStyle()

			css["position"] = "absolute"
			css["margin"] = "0px"
			
			#変形
			if x.transform:
				transform = x.transform.toMatrix()
				css["transform"] = transform
			
			#出力
			self.__css.write(".%s{%s}\n" % (name, str(css)));
		self.__html.write('<div class="%s">\n' % name)
		svg.SVGHandler.group(self, x)
		self.__html.write('</div>\n');
		
	def use(self, x):
		name = self.newName(x)
		css = CSSStyle()
		css["position"] = "absolute"
		css["margin"] = "0px"

		css["left"] = str(-x.width/2)
		css["top"] = str(-x.height/2)
		css["width"] = str(x.width)
		css["height"] = str(x.height)
		
		transform = svg.Transform.Translate(x.x, x.y)
		if x.transform:
			transform = x.transform.toMatrix() * transform
		transform = svg.Transform.Translate(x.width/2, x.height/2) * transform
		css["transform"] = transform

		self.__css.write(".%s{%s}\n" % (name, str(css)));
		self.__html.write('<div class="%s">\n' % name)
		svg.SVGHandler.use(self, x)
		self.__html.write('</div>\n');
		
	def __del__(self):
		self.__html.close()
		self.__css.close()

def main():
	testsets = ["rect", "rect-rotate","ellipse","ellipse-rotate","opacity","droid","gradient","use"]
	for name in testsets:
		p = svg.Parser()
		svgfile = open(name + ".svg", "r")
		writer = CSSWriter(name)
		s = p.parse(svgfile)
		s.callHandler(writer)
	return

if __name__=="__main__":
	main()
