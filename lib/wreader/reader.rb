require 'wreader/db'
require 'json'


module WReader


  class Reader
    attr_reader :metadata, :filename, :db

    def initialize(filename, database=WReader.get_database)
      @filename = filename
      @db = database
    end

    def dims(size=1024)
      w = metadata['Image.Width']
      h = metadata['Image.Height']
      if w and h
        larger = [w.to_f,h.to_f].max.to_f
        wr = (w.to_f / larger) * size
        hr = (h.to_f / larger) * size
        %Q(width="#{wr.ceil}" height="#{hr.ceil}")
      else
        ""
      end
    end

    # return a metadata hash for the filename
    # loads/caches it from/to db if one given
    def metadata
      return @metadata if @metadata
      md = nil
      if db
        json = db.get_first_row(%Q(
          SELECT json FROM metadata WHERE filename = ?
        ), filename)
        md = JSON.parse(json[0]) if json
      end
      unless md
        require 'metadata'
        Metadata.no_text = !db # get full text now, store pages in DB
        Metadata.guess_metadata = true
        pdf = pdf_filename # make temp pdf for non-pdf docs
        md = filename.to_pn.metadata
        if pdf
          Metadata.no_text = true
          Metadata.guess_metadata = false
          md['Doc.PageCount'] = pdf.to_pn.metadata['Doc.PageCount']
        end
        if db
          text = md.delete('File.Content')
          blast_ligatures(text)
          db.execute("BEGIN")
          db.execute(
            "INSERT INTO metadata (filename, json) VALUES (?, ?)",
            filename,
            md.to_json
          )
          if text
            pages = text.split("\f") # split on page breaks
            pages.each_with_index{|txt, i|
              db.execute(
                "INSERT INTO page_texts (filename, page, content) VALUES (?,?,?)",
                filename, i+1, txt
              )
            }
          end
          db.execute("COMMIT")
          md['File.Content'] = pages.join("\n\n") if pages
        end
      end
      @metadata = md
      md
    end

    def get_document_citations
      return [] # TODO
    end

    def get_page_text(page, end_page=nil)
      txt = get_page('text', page, end_page, true){|p1, p2, fn|
        if p1 == 0
          text = `pdftotext -enc UTF-8 #{fn.dump} -`
        else
          text = `pdftotext -f #{p1} -l #{p2} -enc UTF-8 #{fn.dump} -`
        end
        blast_ligatures(text)
        text.split("\f")
      }
      return txt[0] unless end_page
      txt
    end

    def get_page_html(page, end_page=nil)
      get_page('html', page, end_page, !end_page){|p1, p2, fn|
        if p1 == 0
          text = `pdftohtml -enc UTF-8 -stdout #{fn.dump}`
        else
          text = `pdftohtml -f #{p1} -l #{p2} -enc UTF-8 -stdout #{fn.dump}`
        end
        [text]
      }[0]
    end

    def get_page(format, page, end_page, use_db)
      unless %w(html text).include?(format)
        raise(ArgumentError, "Unsupported format #{format}")
      end
      page = 0 unless page
      if use_db
        text = db.execute("
          SELECT content
          FROM page_#{format}s
          WHERE filename = ?
          AND page >= ?
          AND page <= ?
          ORDER BY page ASC", filename, page, end_page || page).map{|r| r[0] }
        return text unless text.empty?
      end
      pdf = pdf_filename
      text = [""]
      text = yield(page, page || end_page, pdf) if pdf
      if use_db
        db.execute("BEGIN")
        (page..(end_page || page)).each{|i|
          db.execute(
            "INSERT INTO page_#{format}s (filename, page, content) VALUES (?, ?, ?)",
            filename, i, text[i-page]
          )
        }
        db.execute("COMMIT")
      end
      text
    end

    def blast_ligatures(text)
      text.gsub!("æ", 'ae')
      text.gsub!("Æ", 'AE')
      text.gsub!("œ", "ce")
      text.gsub!("Œ", "CE")
      text.gsub!("ŋ", "ng")
      text.gsub!("Ŋ", "NG")
      text.gsub!("ʩ", "fng")
      text.gsub!("ﬀ", "ff")
      text.gsub!("ﬁ", "fi")
      text.gsub!("ﬂ", "fl")
      text.gsub!("ﬃ", "ffi")
      text.gsub!("ﬄ", "ffl")
      text.gsub!("ﬅ", "ft")
      text.gsub!("ﬆ", "st")
      text
    end

    def pdf_filename
      if File.extname(filename).downcase == '.pdf'
        pdf = filename
      elsif File.exist?(filename+"-temp.pdf")
        pdf = filename+"-temp.pdf"
      else
        2.times do
          thumbnail(128, true) # make temp pdf for non-pdf docs
          if File.exist?(filename+"-temp.pdf")
            pdf = filename+"-temp.pdf"
            break
          end
        end
      end
      pdf
    end

    def to_png(png_filename, size=1024, page=1)
      tmp_file = File.join(WReader.temp_dir, "#{Process.pid}-#{Time.now.to_f}.png")
      system("thumbnailer",
        "-i", "application/pdf",
        "-s", size.to_s, "-p", (page-1).to_s,
        pdf_filename, tmp_file)
      File.rename(tmp_file, png_filename)
      png_filename
    end

    # make a nice thumbnail
    def thumbnail(size=128, force=false)
      tfn = File.join(WReader.thumb_dir, filename + "-#{size}.png")
      if not File.exist?(tfn) or force
        system("thumbnailer", "-k", "-s", size.to_s, filename, tfn)
      end
      tfn
    end

  end


end
