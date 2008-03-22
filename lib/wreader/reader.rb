require 'wreader/db'
require 'json'

module WReader
  
  class Reader
    attr_reader :metadata, :filename, :db

    def initialize(filename, database)
      @db = database
      @filename = filename
      @metadata = get_metadata
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
    def get_metadata
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
        end
      end
      md
    end

    def get_document_citations
      return [] # TODO
    end

    def get_page_text(page)
      if db
        text = db.get_first_row(%Q(
          SELECT content FROM page_texts WHERE filename = ? AND page = ?
        ), filename, page)
        return text[0] if text
      end
      text = begin
        if File.extname(filename).downcase == '.pdf'
          pdf = filename
        elsif File.exist?(filename+"-temp.pdf")
          pdf = filename+"-temp.pdf"
        end
        `pdftotext -f #{page} -l #{page} -enc UTF-8 -nopgbrk #{pdf} - `.
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
          gsub("ﬆ", "st")
      rescue
        ""
      end
      if db
        db.execute(
          "INSERT INTO page_texts (filename, page, content) VALUES (?, ?, ?)",
          filename, page, text
        )
      end
      text
    end

  end

end
