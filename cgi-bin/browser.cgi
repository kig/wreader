#!/usr/bin/ruby

=begin
  browser.cgi - Browse documents on the web server

  Copyright (C) 2007  Ilmari Heikkinen

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

  http://www.gnu.org/copyleft/gpl.html
=end

$KCODE = 'u'

GC.disable # no need to GC on a CGI script

times = []
times << ['begin', Time.now.to_f]

require 'wreader'
require 'cgi'
require 'uri'

times << ['loaded libs', Time.now.to_f]

cgi = CGI.new('html3')

browser = WReader::Browser.new

header = %Q(
  <h1>Documents</h1>
)
items = %Q(
  <div id="items">
    #{
      browser.items.map do |item|
        cgi.p { cgi.a("reader.cgi?item=" + item.filename){
          cgi.img(item.thumbnail) +
          "<br>" +
          item.metadata['Doc.Title'] || File.basename(item.filename)
        } }
      end
    }
  </div>
)
footer = %Q(
  <br><br>
)

style = %Q(
  <style type="text/stylesheet">
    img {
      border : 0px;
    }
  </style>
)

content = cgi.html{
  cgi.head{
    cgi.title{ "Documents" } +
    style
  } +
  cgi.body {
    header +
    items +
    footer
  }
}
head = cgi.header(
  "type" => "text/html",
  "length" => content.size,
  "status" => "OK"
)
cgi.print(head)
cgi.print(content)
times << ['create HTML', Time.now.to_f]

WReader.print_profile(times)


