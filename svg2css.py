#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import svg

class CSSWriter(svg.SVGHandler):
	def __init__(self, name):
		self.__name = name
		self.__html = open(name + ".html", "w")
		self.__css = open(name + ".css", "w")
		self.__id = 0
		
	def newName(self):
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
		name = self.newName()
		css = {}
		stroke = svg.Length(0)
		
		#ストロークの描画
		if "stroke" in x.style and x.style["stroke"] != 'none':
			try:
				css["border-style"] = "solid"
				if "stroke-opacity" in x.style:
					color = svg.Color(x.style["stroke"])
					color.a = float(x.style["stroke-opacity"])
					css["border-color"] = color.toRGBA()
				else:
					css["border-color"] =  x.style["stroke"]
				stroke = svg.Length(x.style.get("stroke-width",1))
				css["border-width"] = str(stroke)
			except:
				pass
		
		#位置と大きさの設定
		css["position"] = "absolute"
		css["left"] = str(x.x - stroke/2)
		css["top"] = str(x.y - stroke/2)
		css["width"] = str(x.width - stroke)
		css["height"] = str(x.height - stroke)
		
		#角を丸める
		if x.rx and x.ry:
			css["border-radius"] = "%s/%s" % (str(x.rx+stroke/2), str(x.ry+stroke/2))
		elif x.rx:
			css["border-radius"] = str(x.rx+stroke/2)
		elif x.ry:
			css["border-radius"] = str(x.ry+stroke/2)
	
		#変形
		if x.transform:
			#CSSとSVGの原点の違いを補正
			transform = x.transform.toMatrix()
			transform = transform * svg.Transform.Translate(x.x+x.width/2, x.y+x.height/2)
			transform = svg.Transform.Translate(-x.x-x.width/2, -x.y-x.height/2) * transform
			css["transform"] = css["-ms-transform"] = css["-o-transform"] = css["-webkit-transform"] = str(transform)
			css["-moz-transform"] = transform.toStringMoz()

		#フィルを指定する
		if "fill" in x.style and x.style["fill"] != "none":
			try:
				if "fill-opacity" in x.style:
					color = svg.Color(x.style["fill"])
					color.a = float(x.style["fill-opacity"])
					css["background-color"] = color.toRGBA()
				else:
					css["background-color"] = x.style["fill"]
			except:
				pass
			
		#出力
		css_style = "".join(["%s:%s;"%style for style in css.items()])
		self.__css.write(".%s{%s}\n" % (name, css_style));
		self.__html.write('<div class="%s"></div>\n' % name);
	
	def arc(self, x):
		name = self.newName()
		css = {}
		stroke = svg.Length(0)
		
		#ストロークの描画
		if "stroke" in x.style and x.style["stroke"] != 'none':
			try:
				css["border-style"] = "solid"
				if "stroke-opacity" in x.style:
					color = svg.Color(x.style["stroke"])
					color.a = float(x.style["stroke-opacity"])
					css["border-color"] = color.toRGBA()
				else:
					css["border-color"] =  x.style["stroke"]
				stroke = svg.Length(x.style.get("stroke-width",1))
				css["border-width"] = str(stroke)
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
		if "fill" in x.style and x.style["fill"] != "none":
			try:
				if "fill-opacity" in x.style:
					color = svg.Color(x.style["fill"])
					color.a = float(x.style["fill-opacity"])
					css["background-color"] = color.toRGBA()
				else:
					css["background-color"] = x.style["fill"]
			except:
				pass
		
		#変形
		if x.transform:
			#CSSとSVGの原点の違いを補正
			transform = x.transform.toMatrix()
			transform = transform * svg.Transform.Translate(x.cx, x.cy)
			transform = svg.Transform.Translate(-x.cx, -x.cy) * transform
			css["transform"] = css["-ms-transform"] = css["-o-transform"] = css["-webkit-transform"] = str(transform)
			css["-moz-transform"] = transform.toStringMoz()
		
		#出力
		css_style = "".join(["%s:%s;"%style for style in css.items()])
		self.__css.write(".%s{%s}\n" % (name, css_style));
		self.__html.write('<div class="%s"></div>\n' % name);
	
	def group(self, x):
		name = self.newName()
		css = {}
		stroke = svg.Length(0)

		css["position"] = "absolute"
		css["margin"] = "0px"
		
		#変形
		if x.transform:
			css["transform"] = css["-ms-transform"] = css["-o-transform"] = css["-webkit-transform"] = css["-moz-transform"] = str(x.transform)
		
		#出力
		css_style = "".join(["%s:%s;"%style for style in css.items()])
		self.__css.write(".%s{%s}\n" % (name, css_style));
		self.__html.write('<div class="%s">\n' % name)
		svg.SVGHandler.group(self, x)
		self.__html.write('</div>\n');
	
	def __del__(self):
		self.__html.close()
		self.__css.close()

def main():
	testsets = ["rect", "rect-rotate","ellipse","ellipse-rotate","opacity","droid","gradient"]
	for name in testsets:
		p = svg.Parser()
		svgfile = open(name + ".svg", "r")
		writer = CSSWriter(name)
		s = p.parse(svgfile)
		s.callHandler(writer)
	return

if __name__=="__main__":
	main()
