#!/usr/bin/ruby

=begin
  page.cgi - convert.cgi's jpg/png conversion part for documents :->

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

# page.cgi
# item=item_path (2007/10-10-Thu/foo.pdf)
# page=page_num (4)
# size=long_side_in_px (1024)

use_print_profile = true
times = []
times << ['begin', Time.now.to_f]

require 'cgi'
require 'time'
require 'wreader/reader'
require 'wreader/utils'

times << ['loaded libs', Time.now.to_f]

cgi = CGI.new('html3')

if ENV['HTTP_IF_MODIFIED_SINCE']
  head = cgi.header(
    "status" => "NOT_MODIFIED"
  )
  cgi.print(head)
  exit
end


item = cgi['item'].to_s
page = [cgi['page'].to_s.to_i, 1].max
size = [0, [2048, cgi['size'].to_s.to_i].min ].max
size = 1024 if size == 0
type = cgi['type'].to_s.downcase

filename = item
if File.exist?(filename) and File.file?(filename)
  times << ['verified filename', Time.now.to_f]
  if File.extname(filename).downcase == '.pdf'
    pdf = filename
  elsif File.exist?(filename+"-temp.pdf")
    pdf = filename+"-temp.pdf"
  end
  if pdf
    case type
    when 'html'
      page_fn = pdf+"-page-#{page}.html"
      unless File.exist?(page_fn)
        system("pdftohtml -f #{page} -l #{page} -noframes -enc UTF-8 -p -stdout #{pdf} > #{page_fn}")
      end
      type = "text/html"
    when 'txt'
      page_fn = pdf+"-page-#{page}.txt"
      unless File.exist?(page_fn)
        system("pdftotext -f #{page} -l #{page} -enc UTF-8 -nopgbrk #{pdf} - > #{page_fn}")
      end
      type = "text/plain"
    else
      reader = WReader::Reader.new(pdf, nil)
      page_fn = pdf+"-page-#{page}-#{size}.png"
      reader.to_png(page_fn, size, page) unless File.exist?(page_fn)
      pid = fork {
        page_fn = pdf+"-page-#{page+1}-#{size}.png"
        reader.to_png(page_fn, size, page+1) unless File.exist?(page_fn)
        page_fn = pdf+"-page-#{page-1}-#{size}.png"
        reader.to_png(page_fn, size, page-1) unless File.exist?(page_fn)
        exit!(0)
      }
      Process.detach(pid)
      type = "image/png"
    end
    times << ["created file #{page_fn}", Time.now.to_f]
    if File.exist?(page_fn)
      ok_page = true
      head = cgi.header(
        "type" => type,
        "length" => File.size(page_fn),
        "status" => "OK",
        "expires" => Time.now + (86400 * 365),
        "Last-modified" => File.mtime(page_fn).httpdate,
        "Cache-control" => "public, max-age=#{86400*365}"
      )
      cgi.print(head)
      cgi.print(File.read(page_fn))
      times << ["wrote out #{page_fn}", Time.now.to_f]
    end
  end
end
WReader.error(cgi, "Failed to create page") if !ok_page

WReader.print_profile(times) if use_print_profile

