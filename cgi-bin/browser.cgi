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
  <ol id="items">
    #{
      browser.items.
      sort_by{|item| item.metadata['Doc.Title'] || File.basename(item.filename) }.
      map do |item|
        pages = item.metadata['Doc.PageCount']
        words = item.metadata['Doc.WordCount']
        min = (words / 250.0).ceil
        min = "#{min/60}h #{min%60}" if min > 59
        cgi.li { 
          cgi.a("reader.cgi?item=" + item.filename){
            item.metadata['Doc.Title'] || File.basename(item.filename)
          } + 
          %Q[ &mdash; #{pages} pages, #{words} words, ~#{min}min]
        }
      end
    }
  </ol>
)
footer = %Q(
  <br><br>
)

style = %Q(
  <style type="text/css">
    a {
      text-decoration: none;
    }
    a img {
      border: 1px solid black;
      margin-right: 4px;
      vertical-align: middle;
    }
    ol {
      margin-bottom: 2px;
      margin-top: 2px;
      font-size: 0.6em;
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


