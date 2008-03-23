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

require 'wreader'
require 'cgi'
require 'time'

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
WReader.assert_filename(cgi, filename)

times << ['verified filename', Time.now.to_f]
reader = WReader::Reader.new(filename, nil)
pdf = reader.pdf_filename

if pdf
  case type
  when 'html'
    page_fn = pdf+"-page-#{page}.html"
    unless File.exist?(page_fn)
      system("pdftohtml -f #{page} -l #{page} -noframes -enc UTF-8 -p -stdout #{pdf} > #{page_fn}")
    end
    type = "text/html"
  when 'txt'
    data = reader.get_page_text(page)
    type = "text/plain"
  else
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
  if data or File.exist?(page_fn)
    ok_page = true
    head = cgi.header(
      "type" => type,
      "length" => data ? data.size : File.size(page_fn),
      "status" => "OK",
      "expires" => Time.now + (86400 * 365),
      "Last-modified" => File.mtime(data ? pdf : page_fn).httpdate,
      "Cache-control" => "public, max-age=#{86400*365}"
    )
    cgi.print(head)
    cgi.print(data || File.read(page_fn))
    times << ["wrote out #{page_fn}", Time.now.to_f]
  else
    WReader.error(cgi, "Failed to create page")
  end
else
  WReader.error(cgi, "Couldn't find a matching PDF file.")
end


WReader.print_profile(times) if use_print_profile

