#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import svg
import re
import math
import os.path
from optparse import OptionParser

class CSSStyle(dict):
	def __str__(self):
		s = ""
		for name,style in self.iteritems():
			if name=="transform":
				s += CSSStyle.__transform(style)
				continue
			if isinstance(style, list):
				s += "".join(["%s:%s;" % (name, s) for s in style])
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
	
	__re_fill_url = re.compile("url\(#(.*)\)")
	def addFill(self, element):
		svgstyle = element.style
		if "fill" not in svgstyle or svgstyle["fill"] == "none":
			return
			
		try:
			fill = svgstyle["fill"]
			m = CSSStyle.__re_fill_url.match(fill)
			if m:
				fill = element.root.getElementById(m.group(1))
				if isinstance(fill, svg.LinearGradient):
					self.__addLinearGradient(element, fill)
				elif isinstance(fill, svg.RadialGradient):
					self.__addRadialGradient(element, fill)
				return
			color = svg.Color(fill)
			if "fill-opacity" in svgstyle:
				color.a = float(svgstyle["fill-opacity"])
			self["background-color"] = color
		except Exception,e:
			print svgstyle["fill"], e
	
	def __addLinearGradient(self, element, fill):
		root = fill.root
		stops = fill
		while len(stops)==0 and stops.href:
			stops = root.getElementById(stops.href[1:])
		background = []
		
		#座標補正
		point1 = svg.Point(fill.x1, fill.y1)
		point2 = svg.Point(fill.x2, fill.y2)
		point1 = fill.gradientTransform.toMatrix() * point1
		point2 = fill.gradientTransform.toMatrix() * point2
		if fill.gradientUnits == "userSpaceOnUse":
			stroke = svg.Length(element.style.get("stroke-width",0))
			point1 = svg.Point(
				point1.x - svg.Length(self["left"]) - stroke,
				point1.y - svg.Length(self["top"]) - stroke)
			point2 = svg.Point(
				point2.x - svg.Length(self["left"]) - stroke,
				point2.y - svg.Length(self["top"]) - stroke)

		def svgOffsetToPoint(offset):
			return point1*(1-offset) + point2*offset
		
		#css3のデフォルト
		rad = -math.atan2(point2.y-point1.y, point2.x-point1.x)
		vec = svg.Point(math.cos(rad), -math.sin(rad))
		deg = rad/math.pi*180
		width = svg.Length(self["width"])
		height = svg.Length(self["height"])
		point0 = svg.Point(0,0)
		if 0<deg<90:
			point0 = svg.Point(0, height)
		elif 90<=deg:
			point0 = svg.Point(width, height)
		elif deg<-90:
			point0 = svg.Point(width, 0)
		gradientlen = (svg.Point(width, height)-point0*2) * vec

		def pointToCSSOffset(point):
			offset = (point - point0) * vec / gradientlen
			return offset
		
		def svgOffsetToCSSOffset(offset):
			return pointToCSSOffset(svgOffsetToPoint(offset))

		gradient = "(%.1fdeg" % deg
		color_stops = []
		for stop in stops:
			color = svg.Color(stop.style["stop-color"])
			if float(stop.style.get("stop-opacity", "1"))<=0.999:
				color.a = float(stop.style.get("stop-opacity", "1"))
			gradient += ",%s %.1f%%" % (color, svgOffsetToCSSOffset(stop.offset)*100)
			
		gradient += ")"
		background.append("linear-gradient" + gradient)
		background.append("-o-linear-gradient" + gradient)
		background.append("-moz-linear-gradient" + gradient)
		background.append("-ms-linear-gradient" + gradient)
		background.append("-webkit-linear-gradient" + gradient)
		
		#webkit
		webkit = "-webkit-gradient(linear,%f %f,%f %f," % (point1.x.px, point1.y.px, point2.x.px, point2.y.px)
		color = svg.Color(stops[0].style["stop-color"])
		if float(stops[0].style.get("stop-opacity", "1"))<=0.999:
			color.a = float(stops[0].style.get("stop-opacity", "1"))
		webkit += "from(%s)," % color
		if len(stops)>2:
			for stop in stops[1:-1]:
				color = svg.Color(stop.style["stop-color"])
				if float(stop.style.get("stop-opacity", "1"))<=0.999:
					color.a = float(stop.style.get("stop-opacity", "1"))
				webkit += "color-stop(%f,%s)," % (stop.offset, color)
		color = svg.Color(stops[-1].style["stop-color"])
		if float(stops[-1].style.get("stop-opacity", "1"))<=0.999:
			color.a = float(stops[-1].style.get("stop-opacity", "1"))
		webkit += "to(%s))" % color
		background.append(webkit)

		self["background"] = background
		
	def __addRadialGradient(self, element, fill):
		root = fill.root
		stops = fill
		while len(stops)==0 and stops.href:
			stops = root.getElementById(stops.href[1:])
		background = []
		
		#座標補正
		gradientTransform = fill.gradientTransform.toMatrix()
		center = svg.Point(fill.cx, fill.cy)
		finish = svg.Point(fill.fx, fill.fy)
		center = gradientTransform * center
		finish = gradientTransform * finish
		
		if fill.gradientUnits == "userSpaceOnUse":
			stroke = svg.Length(element.style.get("stroke-width",0))
			center = svg.Point(
				center.x - svg.Length(self["left"]) - stroke,
				center.y - svg.Length(self["top"]) - stroke)
			finish = svg.Point(
				finish.x - svg.Length(self["left"]) - stroke,
				finish.y - svg.Length(self["top"]) - stroke)
		
		#半径の決定
		zero = svg.Length("0")
		point0 = gradientTransform * svg.Point(zero, zero)
		rx = svg.Length(abs(gradientTransform * svg.Point(fill.r, zero) - point0), "px")
		ry = svg.Length(abs(gradientTransform * svg.Point(zero, fill.r) - point0), "px")
		r = fill.r
		
		gradient = ""
		for stop in stops:
			color = svg.Color(stop.style["stop-color"])
			if float(stop.style.get("stop-opacity", "1"))<=0.999:
				color.a = float(stop.style.get("stop-opacity", "1"))
			gradient += ",%s %.1f%%" % (color, stop.offset*100)
		background.append("radial-gradient(%s %s,%s %s%s)" % (center.x, center.y, rx, ry, gradient))
		background.append("-o-radial-gradient(%s %s,%s %s%s)" % (center.x, center.y, rx, ry, gradient))
		background.append("-moz-radial-gradient(%s %s,circle%s)" % (center.x, center.y, gradient))
		background.append("-moz-radial-gradient(%s %s,%s %s%s)" % (center.x, center.y, rx, ry, gradient))
		background.append("-ms-radial-gradient(%s %s,%s %s%s)" % (center.x, center.y, rx, ry, gradient))
		background.append("-webkit-radial-gradient(%s %s,%s %s%s)" % (center.x, center.y, rx, ry, gradient))

		self["background"] = background
		
class CSSWriter(svg.SVGHandler):
	def __init__(self, name, html = None, css = None):
		self.__name = name
		self.__html = html or open(name + ".html", "w")
		self.__css = css or open(name + ".css", "w")
		self.__id = 0
		self.__css_classes = set()
		self.__clipnames = {}
		
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
<title>%s</title>
</head>
<body>
<div class="svg">\n""" % (self.__name, self.__name))
		self.__css.write('@charset "utf-8";\n')
		self.__css.write(".svg{top:0px;left:0px;width:%s;height:%s;position:absolute;}\n" % (str(x.width), str(x.height)))
		svg.SVGHandler.svg(self, x)
		self.__html.write("""</div>\n</body></html>\n""")
		
	def rect(self, x):
		name = self.newName(x)
		if name not in self.__css_classes:
			self.__css_classes.add(name)
			css = CSSStyle()
			stroke = svg.Length(0)
			
			#クリップパスの設定
			self.__clipPath(name, x)
			
			#ストロークの描画
			if "stroke" in x.style and x.style["stroke"] != 'none':
				try:
					stroke = svg.Length(x.style.get("stroke-width",0))
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
			css.addFill(x)
				
			#出力
			self.__css.write(".%s{%s}\n" % (name, str(css)))
		
		#クリップの設定
		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self.__html.write('<div class="%s"><div class="%sinverse"><div class="%s"></div></div></div>\n' % (clipname, clipname, name))
			return
		
		self.__html.write('<div class="%s"></div>\n' % name)
	
	def arc(self, x):
		name = self.newName(x)
		if name not in self.__css_classes:
			self.__css_classes.add(name)
			css = CSSStyle()
			stroke = svg.Length(0)
			
			#クリップパスの設定
			self.__clipPath(name, x)
			
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
			css.addFill(x)
			
			#変形
			if x.transform:
				#CSSとSVGの原点の違いを補正
				transform = x.transform.toMatrix()
				transform = transform * svg.Transform.Translate(x.cx, x.cy)
				transform = svg.Transform.Translate(-x.cx, -x.cy) * transform
				css["transform"] = transform
			
			#出力
			self.__css.write(".%s{%s}\n" % (name, str(css)));

		#クリップの設定
		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self.__html.write('<div class="%s"><div class="%sinverse"><div class="%s"></div></div></div>\n' % (clipname, clipname, name))
			return

		self.__html.write('<div class="%s"></div>\n' % name);
	
	def group(self, x):
		name = self.newName(x)
		if name not in self.__css_classes:
			self.__css_classes.add(name)
			css = CSSStyle()

			#クリップパスの設定
			self.__clipPath(name, x)

			css["position"] = "absolute"
			css["margin"] = "0px"
			
			#変形
			if x.transform:
				transform = x.transform.toMatrix()
				css["transform"] = transform
			
			#出力
			self.__css.write(".%s{%s}\n" % (name, str(css)));

		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self.__html.write('<div class="%s"><div class="%sinverse">\n' % (clipname, clipname))

		self.__html.write('<div class="%s">\n' % name)
		svg.SVGHandler.group(self, x)
		self.__html.write('</div>\n');

		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self.__html.write('</div></div>\n')

		
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
	
	def __clipPath(self, element_name, element):
		#クリップパスが設定されているか確認
		if not element.clip_path:
			return
		m = re.match("^url\(#(.*)\)$", element.clip_path)
		if not m:
			return
		
		#クリップパスオブジェクトを取得
		x = element.root.getElementById(m.group(1))
				
		name = self.newName()

		css = CSSStyle()
		invtransform = svg.Transform("")
		if isinstance(x[0], svg.Rect):
			css["position"] = "absolute"
			css["left"] = x[0].x
			css["top"] = x[0].y
			css["width"] = x[0].width
			css["height"] = x[0].height
			if x[0].rx and x[0].ry:
				css["border-radius"] = "%s/%s" % (str(x[0].rx), str(x[0].ry))
			elif x[0].rx:
				css["border-radius"] = x[0].rx
			elif x[0].ry:
				css["border-radius"] = x[0].ry
			
			#座標変換
			if x[0].transform or element.transform:
				#CSSとSVGの原点の違いを補正
				transform = element.transform.toMatrix() * x[0].transform.toMatrix()
				invtransform.append(transform.inverse())
				transform = transform * svg.Transform.Translate(x[0].x+x[0].width/2, x[0].y+x[0].height/2)
				transform = svg.Transform.Translate(-x[0].x-x[0].width/2, -x[0].y-x[0].height/2) * transform
				css["transform"] = transform
			invtransform.append(svg.Transform.Translate(-x[0].x, -x[0].y))

			css["overflow"] = "hidden"
		self.__css.write(".%s{%s}\n" % (name, str(css)));
		
		css = CSSStyle()
		css["position"] = "absolute"
		css["transform"] = invtransform.toMatrix()
		self.__css.write(".%sinverse{%s}\n" % (name, str(css)));
		self.__clipnames[element_name] = name
		
		return name
		
	def __del__(self):
		self.__html.close()
		self.__css.close()

def main():
	#オプション解析
	parser = OptionParser(usage = "usage: %prog [options] svgfile")
	(options, args) = parser.parse_args()
	if len(args)==0:
		parser.print_help()
		return
	
	#SVGファイル取得
	svgfile = open(args[0], "r")
	root, ext = os.path.splitext(args[0])
	name = os.path.basename(root)
	html = open(name + ".html", "w")
	css = open(name + ".css", "w")

	#解析＆変換
	p = svg.Parser()
	writer = CSSWriter(name, html, css)
	s = p.parse(svgfile)
	s.callHandler(writer)
	return

if __name__=="__main__":
	main()
