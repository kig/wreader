#!/usr/bin/ruby

# page.cgi
# item=item_path (2007/10-10-Thu/foo.pdf)
# page=page_num (4)
# size=long_side_in_px (1024)

require 'cgi'
require 'time'

cgi = CGI.new('html3')

if ENV['HTTP_IF_MODIFIED_SINCE']
  head = cgi.header(
    "status" => "NOT_MODIFIED"
  )
  cgi.print(head)
  exit
end

def page_png(pdf, size, page)
  page_fn = pdf+"-page-#{page}-#{size}.png"
  unless File.exist?(page_fn)
    require 'rubygems'
    require 'thumbnailer'
    require 'fileutils'
    tmp_file = "/tmp/page_images_#{ENV['USER']}/#{Process.pid}-#{Time.now.to_f}.png"
    FileUtils.mkdir_p("/tmp/page_images_#{ENV['USER']}")
    Thumbnailer.thumbnail(pdf, tmp_file, size, page-1)
    FileUtils.mv(tmp_file, page_fn)
  end
  page_fn
end


item = cgi['item'].to_s
page = [cgi['page'].to_s.to_i, 1].max
size = [0, [2048, cgi['size'].to_s.to_i].min ].max
size = 1024 if size == 0
type = cgi['type'].to_s.downcase

filename = item
if File.exist?(filename) and File.file?(filename)
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
    when 'txt'
      page_fn = pdf+"-page-#{page}.txt"
      unless File.exist?(page_fn)
        system("pdftotext -f #{page} -l #{page} -enc UTF-8 -nopgbrk #{pdf} - > #{page_fn}")
      end
    else
      page_fn = page_png(pdf, size, page)
      pid = fork {
        page_png(pdf, size, page+1) rescue nil
        page_png(pdf, size, page-1) rescue nil
        exit!(0)
      }
      Process.detach(pid)
    end
    if File.exist?(page_fn)
      ok_page = true
      head = cgi.header(
        "type" => "image/png",
        "length" => File.size(page_fn),
        "status" => "OK",
        "expires" => Time.now + (86400 * 365),
        "Last-modified" => File.mtime(page_fn).httpdate,
        "Cache-control" => "public, max-age=#{86400*365}"
      )
      cgi.print(head)
      cgi.print(File.read(page_fn))
    end
  end
end
if !ok_page
  cgi.out{
    cgi.html{ cgi.body{
      cgi.h2{ "ERROR ERROR" } +
      cgi.p { "item = #{pdf}<br>page = #{page}<br>page_fn = #{page_fn}" }
    } }
  }
end
