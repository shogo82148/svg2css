#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import svg
import re
import math
import os.path
from optparse import OptionParser
import codecs
from xml.sax.saxutils import escape
from xml.sax.saxutils import quoteattr
sys.stdout = codecs.getwriter('utf_8')(sys.stdout)

__re_url = re.compile("url\(#(.*)\)")
def getURL(s):
	global __re_url
	m = __re_url.match(s)
	if m:
		return m.group(1)
	return None

class CSSStyle(dict):
	def __str__(self):
		s = ""
		for name,style in sorted(self.iteritems(), key=lambda x: len(x[0])):
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
		if isinstance(transform, str) or isinstance(transform, unicode):
			s += "-moz-transform:%s;" % transform
		else:
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
				fill = element.getRoot().getElementById(m.group(1))
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
		root = fill.getRoot()
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
		webkit = "-webkit-gradient(linear,%f %f,%f %f," % (point1.x.px(), point1.y.px(), point2.x.px(), point2.y.px())
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
		root = fill.getRoot()
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
	def __init__(self):
		self._css_data = u""
		self._html_data = u""
		self.__id = 0
		self._css_classes = set()
		self.__clipnames = {}
		
	def newName(self, x=None):
		if x and isinstance(x, svg.Element) and x.id:
			return "svg" + x.id
		self.__id = self.__id + 1
		return "id%04d" % self.__id
	
	def _css(self, s=None, cls=None, id=None, style=None):
		if s:
			self._css_data += s
		if cls and style:
			self._css_data += ".%s{%s}\n" % (cls, str(style))
		if id and style:
			self._css_data += "#%s{%s}\n" % (cls, str(style))
	
	def _html(self, s):
		self._html_data += s
	
	def getHTML(self, title="", cssfile=None):
		ret = """<!DOCTYPE html>
<html>
<head> 
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta http-equiv="content-script-type" content="text/javascript" /> 
<meta http-equiv="content-style-type" content="text/css" />
"""
		if cssfile:
			ret += '<link rel="stylesheet" type="text/css" href="%s" />\n' % cssfile
		else:
			ret += '<style type="text/css">\n%s</style>\n' % self._css_data
		ret += '<title>%s</title>\n' % title
		ret += '</head>\n<body>\n' + self._html_data + '</body>\n</html>\n'
		return ret
		
	def getCSS(self):
		return self._css_data
	
	def svg(self, x):
		self._css(".svg{top:0px;left:0px;width:%s;height:%s;position:absolute;}\n" % (str(x.width), str(x.height)))
		self._html('<div class="svg">\n')
		svg.SVGHandler.svg(self, x)
		self._html('</div>\n')
		
	def rect(self, x):
		self.__round_rect(
			element = x,
			x = x.x,
			y = x.y,
			width = x.width,
			height = x.height,
			rx = x.rx,
			ry = x.ry
		)
	
	def arc(self, x):
		self.__round_rect(
			element = x,
			x = x.cx-x.rx,
			y = x.cy-x.ry,
			width = x.rx*2,
			height = x.ry*2,
			rx = x.rx,
			ry = x.ry
		)

	
	def __round_rect(self, element, x, y, width, height, rx = 0, ry = 0):
		blur = 0
		filterURL = getURL(element.style.get("filter", ""))
		if filterURL:
			filter = element.getRoot().getElementById(filterURL)
			if filter and isinstance(filter[0], svg.FEGaussianBlur):
				blur = filter[0].stdDeviation * 1.7
				try:
					self.__blured_round_rect(element, x, y, width, height, rx, ry, blur)
					return
				except:
					pass
	
		name = self.newName(element)
		if name not in self._css_classes:
			self._css_classes.add(name)
			css = CSSStyle()
			stroke = svg.Length(0)
			
			#クリップパスの設定
			self.__clipPath(name, element)
			
			#ストロークの描画
			if "stroke" in element.style and element.style["stroke"] != 'none':
				try:
					stroke = svg.Length(element.style.get("stroke-width",0))
					css["border-width"] = stroke
					css["border-style"] = "solid"
					color = svg.Color(element.style["stroke"])
					if "stroke-opacity" in element.style:
						color.a = float(element.style["stroke-opacity"])
					css["border-color"] = color
				except:
					pass
			
			#位置と大きさの設定
			css["position"] = "absolute"
			css["left"] = x - stroke/2
			css["top"] = y - stroke/2
			css["width"] = width - stroke
			css["height"] = height - stroke
			
			#角を丸める
			if rx and ry:
				css["border-radius"] = "%s/%s" % (str(rx+stroke/2), str(ry+stroke/2))
			elif rx:
				css["border-radius"] = rx+stroke/2
			elif ry:
				css["border-radius"] = ry+stroke/2
		
			#フィルを指定する
			css.addFill(element)
			
			#変形
			if element.transform:
				#CSSとSVGの原点の違いを補正
				transform = element.transform.toMatrix()
				transform = transform * svg.Transform.Translate(x+width/2, y+height/2)
				transform = svg.Transform.Translate(-x-width/2, -y-height/2) * transform
				css["transform"] = transform
			
			#透明度を指定
			if "opacity" in element.style:
				css["opacity"] = element.style["opacity"]
				
			#出力
			self._css(cls=name, style=css)
		
		#クリップの設定
		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self._html('<div class="%s"><div class="%sinverse"><div class="%s"></div></div></div>\n' % (clipname, clipname, name))
			return
		
		self._html('<div class="%s"></div>\n' % name)
	
	def __blured_round_rect(self, element, x, y, width, height, rx = 0, ry = 0, blur=0):
		name = self.newName(element)
		namefill = name + "-fill"
		namestroke = name + "-stroke"
		hasfill = "fill" in element.style and element.style["fill"] != 'none'
		hasstroke = "stroke" in element.style and element.style["stroke"] != 'none'
		
		#フィルの描画
		if not hasstroke and hasfill:
			if namefill not in self._css_classes:
				self._css_classes.add(namefill)
				css = CSSStyle()
			
				#クリップパスの設定
				self.__clipPath(namefill, element)
				
				#位置と大きさの設定
				css["position"] = "absolute"
				css["left"] = x - 10000
				css["top"] = y - 10000
				css["width"] = width
				css["height"] = height
			
				#角を丸める
				if rx and ry:
					css["border-radius"] = "%s/%s" % (rx, ry)
				elif rx:
					css["border-radius"] = rx
				elif ry:
					css["border-radius"] = ry
			
				#フィルを指定する
				css.addFill(element)
			
				#ぼかしを適用
				css["box-shadow"] = "10000px 10000px %s %s" % (blur, css["background-color"])
				css["-webkit-box-shadow"] = "10000px 10000px %s %s" % (blur*1.8, css["background-color"])
				css["-o-box-shadow"] = "10000px 10000px %s %s" % (blur*1.8, css["background-color"])

				#変形
				if element.transform:
					#CSSとSVGの原点の違いを補正
					transform = element.transform.toMatrix()
					transform = transform * svg.Transform.Translate(x+width/2, y+height/2)
					transform = svg.Transform.Translate(-x-width/2, -y-height/2) * transform
					css["transform"] = transform

					#透明度を指定
				if "opacity" in element.style:
					css["opacity"] = element.style["opacity"]

				#出力
				self._css(cls=namefill, style=css)
		
			#クリップの設定
			if namefill in self.__clipnames:
				clipname = self.__clipnames[namefill]
				self._html('<div class="%s"><div class="%sinverse"><div class="%s"></div></div></div>\n' % (clipname, clipname, name))
				return
			
			self._html('<div class="%s"></div>\n' % namefill)
		
		#ストロークの描画
		if hasstroke:
			if namestroke not in self._css_classes:
				self._css_classes.add(namestroke)
				css = CSSStyle()
			
				#クリップパスの設定
				self.__clipPath(namestroke, element)
				
				#位置と大きさの設定
				css["position"] = "absolute"
				css["left"] = x
				css["top"] = y
				css["width"] = width
				css["height"] = height
			
				#角を丸める
				if rx and ry:
					css["border-radius"] = "%s/%s" % (str(rx), str(ry))
				elif rx:
					css["border-radius"] = rx
				elif ry:
					css["border-radius"] = ry
			
				#ぼかしを適用
				stroke = svg.Length(element.style.get("stroke-width",0))
				color = svg.Color(element.style["stroke"])
				if "stroke-opacity" in element.style:
					color.a = float(element.style["stroke-opacity"])
				css["box-shadow"] = "0px 0px %s %s %s" % (blur, stroke/2, color) + ", 0px 0px %s %s %s inset" % (blur, stroke/2, color)

				#フィルを指定する
				css.addFill(element)

				#変形
				if element.transform:
					#CSSとSVGの原点の違いを補正
					transform = element.transform.toMatrix()
					transform = transform * svg.Transform.Translate(x+width/2, y+height/2)
					transform = svg.Transform.Translate(-x-width/2, -y-height/2) * transform
					css["transform"] = transform

				#透明度を指定
				if "opacity" in element.style:
					css["opacity"] = element.style["opacity"]

				#出力
				self._css(cls=namestroke, style=css)
		
			#クリップの設定
			if namestroke in self.__clipnames:
				namestroke = self.__clipnames[name]
				self._html('<div class="%s"><div class="%sinverse"><div class="%s"></div></div></div>\n' % (clipname, clipname, name))
				return
			
			self._html('<div class="%s"></div>\n' % namestroke)

	def group(self, x):
		name = self.newName(x)
		if name not in self._css_classes:
			self._css_classes.add(name)
			css = CSSStyle()

			#クリップパスの設定
			self.__clipPath(name, x)

			css["position"] = "absolute"
			css["margin"] = "0px"
			
			#変形
			if x.transform:
				transform = x.transform.toMatrix()
				css["transform"] = transform

			#透明度を指定
			if "opacity" in x.style:
				css["opacity"] = x.style["opacity"]

			if x.style.get("display", "inline")=="none":
				css["display"] = "none"

			#出力
			self._css(cls=name, style=css)

		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self._html('<div class="%s"><div class="%sinverse">\n' % (clipname, clipname))

		self._html('<div class="%s">\n' % name)
		svg.SVGHandler.group(self, x)
		self._html('</div>\n');

		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self._html('</div></div>\n')

		
	def use(self, x):
		name = self.newName(x)
		css = CSSStyle()
		css["position"] = "absolute"
		css["margin"] = "0px"
		
		transform = svg.Transform.Translate(x.x, x.y)
		if x.transform:
			transform = x.transform.toMatrix() * transform
		css["transform"] = transform

		#透明度を指定
		if "opacity" in x.style:
			css["opacity"] = x.style["opacity"]

		self._css(cls=name, style=css)
		self._html('<div class="%s">\n' % name)
		svg.SVGHandler.use(self, x)
		self._html('</div>\n');
	
	def __clipPath(self, element_name, element):
		#クリップパスが設定されているか確認
		if not element.clip_path:
			return
		m = re.match("^url\(#(.*)\)$", element.clip_path)
		if not m:
			return
		
		#クリップパスオブジェクトを取得
		x = element.getRoot().getElementById(m.group(1))
				
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
		self._css(cls=name, style=css)
		
		css = CSSStyle()
		css["position"] = "absolute"
		css["transform"] = invtransform.toMatrix()
		self._css(cls=name+"inverse", style=css)
		self.__clipnames[element_name] = name
		
		return name
	
	#テキスト
	def text(self, x):
		name = self.newName(x)
		
		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self._html('<div class="%s"><div class="%sinverse">\n' % (clipname, clipname))
			
		blur = 0
		filterURL = getURL(x.style.get("filter", ""))
		if filterURL:
			filter = x.getRoot().getElementById(filterURL)
			if filter and isinstance(filter[0], svg.FEGaussianBlur):
				blur = filter[0].stdDeviation * 1.7

		self._html('<div class="%s"><span class="svg-text-adj">&nbsp;</span>' % name)
		for a in x:
			if isinstance(a, svg.TSpan):
				self.__text_contents(a, x.x, x.y, blur)
			elif isinstance(a, svg.Characters):
				self._html(a.content)
		self._html('</div>\n');

		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self._html('</div></div>\n')

		#スタイル定義を出力
		if name not in self._css_classes:
			self._css_classes.add(name)
			css = CSSStyle()

			#クリップパスの設定
			self.__clipPath(name, x)

			css["position"] = "absolute"
			css["margin"] = "0px"
			
			#フォントに関する属性をコピー
			if "font-size" in x.style:
				css["font-size"] = svg.Length(x.style["font-size"])
			if "fill" in x.style:
				css["color"] = svg.Color(x.style["fill"])
				if "fill-opacity" in x.style:
					css["color"].a = float(x.style["fill-opacity"])
				if blur>0.001:
					css["text-shadow"] = "0px 0px %s %s" % (blur, css["color"])
					css["color"] = [css["color"], svg.Color(0,0,0,0)]
					
			for stylename in ["font-style", "font-weight", "font-family"]:
				if stylename in x.style:
					css[stylename] = x.style[stylename]
			css["left"] = x.x
			css["top"] = x.y - svg.Length("1000px")
			
			#変形
			if x.transform:
				transform = x.transform.toMatrix()
				css["transform"] = transform
			
			css["white-space"] = "pre"
			
			#出力
			self._css(cls=name, style=css)
			
		if "svg-text-adj" not in self._css_classes:
			self._css_classes.add("svg-text-adj")
			self._css(".svg-text-adj{font-size:0px;vertical-align: 1000px;}\n")

	#テキストの中身
	def __text_contents(self, x, x0=0, y0=0, blur=0):
		name = self.newName(x)
		if name not in self._css_classes:
			self._css_classes.add(name)
			css = CSSStyle()

			#フォントに関する属性をコピー
			if "font-size" in x.style:
				css["font-size"] = svg.Length(x.style["font-size"])
			if "fill" in x.style:
				css["color"] = svg.Color(x.style["fill"])
				if "fill-opacity" in x.style:
					css["color"].a = float(x.style["fill-opacity"])
				if blur>0.001:
					css["text-shadow"] = "0px 0px %s %s" % (blur, css["color"])
					css["color"] = [css["color"], svg.Color(0,0,0,0)]
			for stylename in ["font-style", "font-weight", "font-family"]:
				if stylename in x.style:
					css[stylename] = x.style[stylename]
			
			if x.role=="line":
				css["display"] = "block"
			
			if x.x or x.y:
				css["position"] = "absolute"
				css["left"] = x.x - x0
				css["top"] = x.y - y0
			
			#出力
			self._css(cls=name, style=css)

		self._html('<span class="%s">' % name)
		if x.x or x.y:
			self._html('<span class="svg-text-adj">&nbsp;</span>')
		for a in x:
			if isinstance(a, svg.TSpan):
				self.__text_contents(a, x.x, x.y, blur)
			elif isinstance(a, svg.Characters):
				self._html(escape(a.content))
		self._html('</span>')
	
	def image(self, x):
		name = self.newName(x)
		if name not in self._css_classes:
			self._css_classes.add(name)
			css = CSSStyle()
			stroke = svg.Length(0)
			
			#クリップパスの設定
			self.__clipPath(name, x)
			
			#位置と大きさの設定
			css["position"] = "absolute"
			css["left"] = x.x
			css["top"] = x.y
			css["width"] = x.width
			css["height"] = x.height
			
			#変形
			if x.transform:
				#CSSとSVGの原点の違いを補正
				transform = x.transform.toMatrix()
				transform = transform * svg.Transform.Translate(x.x+x.width/2, x.y+x.height/2)
				transform = svg.Transform.Translate(-x.x-x.width/2, -x.y-x.height/2) * transform
				css["transform"] = transform

			#出力
			self._css(cls=name, style=css)
		
		#クリップの設定
		if name in self.__clipnames:
			clipname = self.__clipnames[name]
			self._html('<div class="%s"><div class="%sinverse"><image class="%s" src=%s /></div></div>\n' % (clipname, clipname, name, quoteattr(os.path.basename(x.href))))
			return
		
		self._html('<image class="%s" src=%s />\n' % (name, quoteattr(os.path.basename(x.href))))
		
class SlideWriter(CSSWriter):
	slide_prefix = "slide"
	container_prefix = "container"
	slide_layer = "slidelayer"
	
	#標準的なディスプレイのサイズ
	display_sizes = [
		(640, 480),
		(800, 600),
		(1024, 768),
		(1280, 800),
		(1280, 1024),
		(1366, 768),
		(1680, 1050),
		(1920, 1080),
		(1920, 1200),
	]

	#スライドの枚数を数えるクラス
	class CountSlide(svg.SVGHandler):
		def __init__(self, html, css):
			self.slides = 0
			self._html = html
			self._css = css
		
		def group(self, x):
			if x.groupmode!="layer":
				return
			self.slides += 1
			name = SlideWriter.slide_prefix + str(self.slides)
			
			css = CSSStyle()
			css["transform"] = "translateX(-%d%%)" % (self.slides * 100)
			self._css("#%s:target .%s {%s}\n" % (name, SlideWriter.container_prefix, str(css)));
			self._css("#%s{left:%d%%}\n" % (SlideWriter.container_prefix + str(self.slides), self.slides*100))
			self._html('<div id="%s">' % name)
		
		def printEndTags(self):
			self._html("</div>" * self.slides + "\n")
	
	def __init__(self):
		CSSWriter.__init__(self)
		self.__slides = 0
		self.__all_slides = 0
		self.__width = 0
		self.__height = 0
		self.__scales = [("100%", 1), ("128%", 1.28), ("160%", 1.6)]
	
	#自動サイズ調整用CSSを出力
	def autosize(self):
		w0 = float(self.__width)
		h0 = float(self.__height)
		sizes = sorted(SlideWriter.display_sizes)
		for i, size in enumerate(sizes):
			w, h = size
			scale = min(w/w0, h/h0)
			css = CSSStyle()
			css['transform'] = "scale(%f)" % scale
			self._css("""@media screen and (min-device-width:%dpx) and (min-device-height:%dpx) {.slidelayer{%s}}\n""" % (w, h, str(css)))
		
	def svg(self, x):
		self._html('<div class="svg">')
		
		#サイズ設定
		self._css(".svg{top:0px;left:0px;width:100%;height:100%;position:absolute;overflow: hidden;}\n" )
		self.__width = x.width
		self.__height = x.height
		self._css(""".%s {
position: absolute; 
width: 100%%; 
height: 100%%; }\n""" % SlideWriter.container_prefix)
		self.autosize()
		
		#アニメーションの設定
		self._css(""".%s {
-ms-transition: -ms-transform 0.8s;
-webkit-transition: -webkit-transform 0.8s;
-moz-transition: -moz-transform 0.8s;
-o-transition: -o-transform 0.8s; }\n""" % SlideWriter.container_prefix)

		#初期位置の設定
		self._css(""".%s {
overflow: hidden;
transform: translateX(-100%%);
-ms-transform: translateX(-100%%);
-webkit-transform: translateX(-100%%);
-moz-transform: translateX(-100%%);
-o-transform: translateX(-100%%);
}\n""" % SlideWriter.container_prefix)
		
		#スライドの内容についての設定
		self._css(""".%s {
top:50%%;
left:50%%;
width: %s;
height: %s;
margin: %s %s;
position:relative;
overflow:hidden;
-ms-transition: 0.4s;
-webkit-transition: 0.4s;
-moz-transition: 0.4s;
-o-transition: 0.4s;
transition: 0.4s;
}
""" % (SlideWriter.slide_layer, self.__width, self.__height, -self.__height/2, -self.__width/2));

		#スライド移動ボタンの設定
		self._css(""".nextbutton, .backbutton {
position:absolute;
top:0px;
height:100%;
width:50%;
margin:0px;
padding:0px;}
.nextbutton {right: 0px}
.backbutton {left: 0px}
#unsupport div {text-align: center; font-size:30px;}
""")

		#メニュー
		self._css("""#menu{
width: 100%;
height: 60px;
position: absolute;
bottom: 0px;
opacity: 0;
-ms-transition: 0.4s;
-webkit-transition: 0.4s;
-moz-transition: 0.4s;
-o-transition: 0.4s;
transition: 0.4s;
}
#menu:hover {
opacity: 1;
}
#navi {
list-style:none;
margin: 0px;
padding: 0px;
}
#navi li{
float:left;
margin: 3px;
}
#navi li a {
padding: 5px 0px 0px 0px;
margin: 0px;
width:25px;
height:20px;
font-size: 15px;
font-weight: bold;
text-decoration: none;
color:black;
display:block;
text-align: center;
vertical-align: middle;
border: 2px solid black;
border-radius: 14px;
background-color: white;
opacity: 0.5;
-ms-transition: 0.4s;
-webkit-transition: 0.4s;
-moz-transition: 0.4s;
-o-transition: 0.4s;
transition: 0.4s;
}
#navi li a:hover{
opacity: 1;
}
""")

		#スケール調整用ラジオボタン
		self._css('input.scaleradio{display:none;}')
		for i in range(len(self.__scales)):
			self._html('<input id="scale%d" type="radio" name="scaleradio" class="scaleradio"/>' % i)
		
		#スライドの開始タグを出力
		counter = SlideWriter.CountSlide(self._html, self._css)
		x.callHandler(counter)
		self.__all_slides = counter.slides
		
		#非対応ブラウザ向けの表示
		self._html(u"""
<div id="unsupport" class="container">
<div>Sorry, This page doesn't support your browser</div>
<div>現在使用中のブラウザでは見れません</div>
</div>
""")
		
		#内容を出力
		svg.SVGHandler.svg(self, x)
		
		#メニュー
		self._html("""<div id="menu">""")
		self._html("""<ul id="navi">""")
		for i in range(self.__all_slides):
			self._html('<li><a id="navibutton%d" href="#%s%d">%d</a></li>' % (i+1, SlideWriter.slide_prefix, i+1, i+1))
			self._css('#%s%d:target #navibutton%d{opacity: 1;}\n' % (SlideWriter.slide_prefix, i+1, i+1))
		self._html("""</ul>""")
		
		for i, t in enumerate(self.__scales):
			self._html('<label for="scale%d">%s</label>' % (i, t[0]))
			self._css("""#scale%d:checked ~ div *.slidelayer{
-webkit-transform:scale(%f);-o-transform:scale(%f);-moz-transform:scale(%f);-ms-transform:scale(%f);transform:scale(%f);}
#scale%d:checked ~div * label[for="scale%d"]{outline: dotted 2px #f93;}
""" % (i, t[1], t[1], t[1], t[1], t[1], i, i))
			
		self._html("""</div>""")
		
		#スライドの終了タグを出力
		counter.printEndTags()
		self._html("""</div></body></html>\n""")

	def group(self, x):
		if x.groupmode!="layer":
			CSSWriter.group(self, x)
		else:
			self.__slides += 1
			name = SlideWriter.container_prefix + str(self.__slides)
			self._html('<div id="%s" class="%s">\n' % (name, SlideWriter.container_prefix))

			#スライドの内容を出力
			self._html('<div class="%s">\n' % SlideWriter.slide_layer)
			svg.SVGHandler.group(self, x)
			self._html('</div>\n')
			
			#移動ボタン
			backslide = self.__slides-1
			nextslide = self.__slides+1
			if backslide<=0:
				backslide = self.__all_slides
			if nextslide>self.__all_slides:
				nextslide = 1
			self._html('<a href="#slide%d" class="backbutton"></a>\n' % backslide)
			self._html('<a href="#slide%d" class="nextbutton"></a>\n' % nextslide)

			self._html('</div>\n')


def main():
	#オプション解析
	parser = OptionParser(usage = "usage: %prog [options] svgfile")
	parser.add_option("-s", "--slide", dest="slide",
		action="store_true", default=False, help="Make slides")
	parser.add_option("--html", dest="html", help="Output HTML File")
	parser.add_option("--css", dest="css", help="Output CSS File")
	(options, args) = parser.parse_args()
	if len(args)==0:
		parser.print_help()
		return
	
	#SVGファイル取得
	svgfile = open(args[0], "r")

	#解析＆変換
	p = svg.Parser()
	if options.slide:
		writer = SlideWriter()
	else:
		writer = CSSWriter()
	s = p.parse(svgfile)
	s.callHandler(writer)
	
	#書き出し
	html_data = ""
	if options.css:
		html_data = writer.getHTML(cssfile=options.css)
		css = codecs.open(options.css, "w", "utf-8")
		css.write(writer.getCSS())
	else:
		html_data = writer.getHTML()
	
	html = sys.stdout
	if options.html:
		html = codecs.open(options.html, "w", "utf-8")
	html.write(html_data)
	
	return

if __name__=="__main__":
	main()