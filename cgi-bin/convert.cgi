#!/usr/bin/ruby

# convert.cgi
# item=item_path (2007/10-10-Thu/foo.pdf)
# type=jpg|pdf|mp3|txt|html
# [page=page_num] (4)

def not_found(cgi, path, type)
  cgi.out("type"=>"text/html", "status"=>"NOT FOUND"){
    cgi.html{
      cgi.head{
        cgi.title{ "Not found: #{CGI.escapeHTML(path)} -> #{type}" }
      } +
      cgi.body{
        cgi.h1{ "Not found: #{CGI.escapeHTML(path)} -> #{type}" }
      }
    }
  }
end

$KCODE = 'u'

require 'cgi'
require 'metadata'
require 'uri'

cgi = CGI.new("html3")

path = cgi['item'].to_s
type = cgi['type'].to_s
page = cgi['page'].to_s.to_i

item = path.to_pn

# FIXME handle softlinks
if item.exist? and item.file?
  case type
  when 'jpg'
    # TODO implement convert to JPEG (use page query var)
  when 'png'
    # TODO implement convert to PNG (use page query var)
  when 'pdf' # TODO use page query var to crop the pages?
    if item.mimetype == 'application/pdf'
      pdf = item.to_s
    elsif File.exist?(item.to_s+"-temp.pdf")
      pdf = item.to_s+"-temp.pdf"
    end
    if pdf
      cgi.print(cgi.header(
        "type" => "application/pdf",
        "expires" => Time.now + (86400 * 365),
        "Content-disposition" => "attachment; filename=#{URI.escape(File.basename(item.to_s))}.pdf;"
      ))
      File.open(pdf,'rb'){|f|
        cgi.print(f.read(32768)) until f.eof?
      }
    else
      not_found(cgi, path, type)
    end
  when 'mp3'
    case item.mimetype.to_s
    when 'audio/mpeg'
      bitrate = cgi['bitrate'].to_s.to_i
      if bitrate == 0 or (bitrate >= item.metadata['Audio.Bitrate'].to_i and [11025, 22050, 44100].include?(item.metadata['Audio.Samplerate'] .to_i))
        header = cgi.header(
          "type" => "audio/mpeg",
          "Content-disposition" => "attachment; filename=#{URI.escape(item.basename)}.mp3;",
          "Content-length" => item.size
        )
        cgi.print(header)
        STDOUT.flush
        # STDERR.puts("sending file "+item.to_s)
        # FIXME attack vector with filename?
        exec("cat #{item.to_s.dump}")
      else
        ib = item.metadata['Audio.Bitrate'].to_i
        if ib != 0
          bitrate = [ib, bitrate].min
        end
        dur = item.length.to_f
        clen = 418 + (dur * bitrate * 125).round
        header = cgi.header(
          "type" => "audio/mpeg",
          "Content-disposition" => "attachment; filename=#{URI.escape(item.basename)}.mp3;",
          "Connection" => "close",
          "Content-length" => clen
        )
        cgi.print(header)
        STDOUT.flush
        STDERR.puts("re-encoding file "+item.to_s)
        bytes_per_sec = 1.1 * bitrate * 125
        secs_per_4k = 4096 / bytes_per_sec
        counter = 20
        # FIXME attack vector with nasty filenames?
        # TODO cache or pregen the resampled mp3s 
        IO.popen("lame --mp3input --resample #{bitrate < 24 ? 11.025 : (bitrate < 96 ? 22.05 : 44.1)} -b #{bitrate} #{item.to_s.dump} - 2>/dev/null", "rb"){|f|
          until f.eof?
            t = Time.now.to_f
            STDOUT.write f.read(4096)
            elapsed = Time.now.to_f - t
            # send first 80kB as fast as possible to avoid audio glitch
            if counter > 1
              counter -= 1
            else # cap send rate to use less CPU
              sleep([0, secs_per_4k-elapsed].max)
            end
          end
        }
      end
    else
      header = cgi.header(
        "type" => "audio/mpeg",
        "Content-disposition" => "attachment; filename=#{URI.escape(File.basename(item.to_s))}.mp3;"
      )
      cgi.print(header)
      STDOUT.flush
      # TODO get this from text cache
      # TODO use page query var to crop
      text = item.metadata['File.Content']
      dot = "."
      # TODO cache this somewhere
      IO.popen('uni2ascii -cdexf | text2mp3', 'rb+'){|f|
        done = false
        t = Thread.new{
          while b=f.read(4096)
            cgi.print(b)
          end
        }
        begin
          text.each_line{|l|
            f.puts(
              l.chomp.
                gsub("æ", 'ae').
                gsub("Æ", 'AE').
                gsub("œ", "ce").
                gsub("Œ", "CE").
                gsub("ŋ", "ng").
                gsub("Ŋ", "NG").
                gsub("ʩ", "fng").
                gsub("ﬀ", "ff").
                gsub("ﬁ", "fi").
                gsub("ﬂ", "fl").
                gsub("ﬃ", "ffi").
                gsub("ﬄ", "ffl").
                gsub("ﬅ", "ft").
                gsub("ﬆ", "st") + '.'
            )
          }
        rescue
        end
        done = true
        f.close_write
        t.join
      }
    end
  when 'txt'
    # TODO how about using a DATA-BASE in-stead?
    text_fn = File.join(item.to_s) + "-temp.txt"
    if not File.exist?(text_fn)
      File.open(text_fn,'wb'){|f|
        txt = item.metadata['File.Content']
        f.write(txt)
      }
    end
    cgi.print(cgi.header(
      "type" => "text/plain",
      "expires" => Time.now + (86400 * 365),
      "Content-disposition" => "inline; filename=#{URI.escape(File.basename(item.to_s))}.txt;"
    ))
    File.open(text_fn,'rb'){|f|
      cgi.print(f.read(32768)) until f.eof?
    }
  when 'html'
    # TODO implement html converter, use pdftohtml and temp pdfs for documents
  else
    cgi.out("text/plain"){ "unknown type #{type}" }
  end
else
  not_found(cgi, path, type)
end