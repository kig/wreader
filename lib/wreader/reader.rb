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
        md = filename.to_pn.metadata
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
      if db
        text = db.execute("
          SELECT content
          FROM page_texts
          WHERE filename = ?
          AND page >= ?
          AND page <= ?
          ORDER BY page ASC", filename, page, end_page || page).map{|r| r[0] }
        return text[0] unless end_page
        return text if text
      end
      pdf = pdf_filename
      if pdf
        text =`pdftotext -f #{page} -l #{end_page || page} -enc UTF-8 #{pdf.dump} -`
        blast_ligatures(text)
      else
        text = ""
      end
      text = text.split("\f")
      if db
        db.execute("BEGIN")
        (page..(end_page || page)).each{|i|
          db.execute(
            "INSERT INTO page_texts (filename, page, content) VALUES (?, ?, ?)",
            filename, i, text[i-page]
          )
        }
        db.execute("COMMIT")
      end
      return text[0] unless end_page
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
      end
      pdf
    end

    def to_png(png_filename, size=1024, page=1)
      system("thumbnailer",
        "-i", "application/pdf", "-k",
        "-s", size.to_s, "-p", (page-1).to_s,
        pdf_filename, png_filename)
      png_filename
    end

  end


end
