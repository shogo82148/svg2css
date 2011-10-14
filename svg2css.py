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
		self.__css.write('@charset "utf-8"\n\n')
		self.__css.write("div.svg{width:%s;height: %s;position: absolute;}\n" % (str(x.width), str(x.height)))
		svg.SVGHandler.svg(self, x)
		self.__html.write("""</div>\n</body></html>\n""")
		
	def rect(self, x):
		name = self.newName()
		css = {}
		stroke = svg.Length(0)
		
		#ストロークの描画
		if "stroke" in x.style and x.style["stroke"] != 'none':
			css["border-style"] = "solid"
			css["border-color"] =  x.style["stroke"]
			stroke = svg.Length(x.style.get("stroke-width",1))
			css["border-width"] = str(stroke)
		
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
			css["-moz-transform"] = x.transform
			css["-webkit-transform"] = x.transform
			css["-o-transform"] = x.transform
			css["-ms-transform"] = x.transform
			print x.transform

		#フィルを指定する
		if "fill" in x.style:
			css["background-color"] = x.style["fill"]
			
		#出力
		css_style = "".join(["%s:%s;"%style for style in css.items()])
		self.__css.write("div.%s{%s}\n" % (name, css_style));
		self.__html.write('<div class="%s"></div>\n' % name);
	
	def arc(self, x):
		name = self.newName()
		css = {}
		stroke = svg.Length(0)
		
		#ストロークの描画
		if "stroke" in x.style and x.style["stroke"] != 'none':
			css["border-style"] = "solid"
			css["border-color"] =  x.style["stroke"]
			stroke = svg.Length(x.style.get("stroke-width",1))
			css["border-width"] = str(stroke)
		
		#位置と大きさの設定
		css["position"] = "absolute"
		css["left"] = str(x.cx - x.rx - stroke/2)
		css["top"] = str(x.cy - x.ry - stroke/2)
		css["width"] = str(x.rx * 2 - stroke)
		css["height"] = str(x.ry * 2 - stroke)
		
		#角を丸める
		css["border-radius"] = "%s/%s" % (str(x.rx+stroke/2), str(x.ry+stroke/2))
	
		#フィルを指定する
		if "fill" in x.style:
			css["background-color"] = x.style["fill"]
		
		#変形
		if x.transform:
			css["-moz-transform"] = x.transform
			css["-webkit-transform"] = x.transform
			css["-o-transform"] = x.transform
			css["-ms-transform"] = x.transform
			print x.transform
		
		#出力
		css_style = "".join(["%s:%s;"%style for style in css.items()])
		self.__css.write("div.%s{%s}\n" % (name, css_style));
		self.__html.write('<div class="%s"></div>\n' % name);
		
	def __del__(self):
		self.__html.close()
		self.__css.close()

def main():
	filename = sys.argv[1]
	p = svg.Parser()
	p.parse(open(filename, "r")).callHandler(CSSWriter("out"))
	return

if __name__=="__main__":
	main()
