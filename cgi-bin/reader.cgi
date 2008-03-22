#!/usr/bin/ruby

=begin
  reader.cgi - Read documents on the web server

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

# reader.cgi
# item=item_path (2007/10-10-Thu/foo.pdf)
# page=page_num (4)

# overwrite this with your own code
def get_database
  if File.exist?("reader.db")
    db = SQLite3::Database.new( "reader.db" )
  else
    db = SQLite3::Database.new( "reader.db" )
    db.execute(%Q(
      CREATE TABLE metadata (
        filename TEXT UNIQUE NOT NULL,
        json TEXT
      )
    ))
    db.execute(%Q(
      CREATE TABLE page_texts (
        filename TEXT NOT NULL,
        page INTEGER NOT NULL,
        content TEXT
      )
    ))
    db.execute(%Q(CREATE INDEX page_texts_filename_idx ON page_texts(filename)))
    db.execute(%Q(
      CREATE UNIQUE INDEX page_texts_filename_page_idx
      ON page_texts(filename, page);
    ))
  end
  db
end

def dims(metadata, size=1024)
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
def get_metadata(filename, db=nil)
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

def get_document_citations(filename, metadata, db=nil)
  return [] # TODO
end

def get_page_text(filename, page, db=nil)
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

def error(cgi, msg)
  cgi.out("status" => "SERVER_ERROR"){
    cgi.html{ cgi.body{
      cgi.h2{
        "ERROR in
         #{ CGI.escapeHTML cgi.script_name.to_s }
         #{ CGI.escapeHTML cgi.query_string.to_s }"
      } +
      cgi.p { msg }
    } }
  }
  exit
end

def print_profile(times)
  return if times.empty?
  prev = times[0][1]
  times.each{|t|
    STDERR.puts("#{interval_bar(prev, t[1])} #{t[0]}")
    prev = t[1]
  }
  STDERR.puts
end

def interval_bar(a, b)
  a ||= b
  ms = (b - a) * 1000
  "[#{("#"*([16, (ms*2).round].min)).rjust(16)}] %.3fms" % [ms]
end

use_print_profile = true
times = []
times << ['begin', Time.now.to_f]

require 'sqlite3'
require 'json'
require 'cgi'
require 'uri'

times << ['loaded libs', Time.now.to_f]

cgi = CGI.new('html3')

db = get_database
times << ['get_database', Time.now.to_f]

unless cgi.has_key?('page')
  head = cgi.header(
    "status" => "MOVED",
    "location" => 'reader.cgi?' + ENV['QUERY_STRING'] + '&page=1'
  )
  cgi.print(head)
  exit
end

filename = cgi['item'].to_s
# FIXME handle softlinks
good_filename = File.expand_path(filename).index(File.expand_path(".")) == 0
error(cgi, "Bad filename.") unless good_filename
error(cgi, "No such file.") unless File.exist?(filename) and File.file?(filename)
times << ['filename', Time.now.to_f]

metadata = get_metadata(filename, db)
page = [cgi['page'].to_i, 1].max
times << ['metadata', Time.now.to_f]

pg = metadata['Doc.PageCount']
error(cgi, "Failed to get page count of document.", filename, page) if pg.nil?
pages = [1, pg.to_i].max

page_text = get_page_text(filename, page, db)
times << ['page text', Time.now.to_f]

cites = get_document_citations(filename, metadata, db)
citation_links = cites.map{|c|
  if c['URL']
    cgi.a(c['URL']){ c['Title'] }
  else
    c['Title']
  end + (c['Authors'].empty? ? "" : " - " + c['Authors'].join(", "))
}
times << ['cites', Time.now.to_f]

uri_pre = "reader.cgi?item=#{URI.escape(filename)}&page="
page_pre = "page.cgi?item=#{URI.escape(filename)}&page="

short_pages_div = %Q(
        <div class="short_pages" id="top_navigation">
          #{
            if page > 1
              %Q(<a href="#{uri_pre}#{page-1}">&larr;prev</a>)
            else
              "&larr;prev"
            end
          }
          #{
            if page < pages
              %Q(<a href="#{uri_pre}#{page+1}">next&rarr;</a>)
            else
              "next&rarr;"
            end
          }
          <span id="page_list">
          [ #{
            if page == 12
              %Q(<a href="1">1</a> )
            elsif page > 12
              %Q(<a href="#{uri_pre}1">1</a> <a href="#pagelist">...</a> )
            end
          }
          #{
            sp = [1, page-10].max
            (sp..[sp+20, pages].min).map{|i|
              if i == page
                %Q(<span class="current">#{i}</span>)
              else
                %Q(<a href="#{uri_pre}#{i}">#{i}</a>)
              end
            }.compact.join(" ")
          }
          #{
            if page == pages-11
              %Q( <a href="#{uri_pre}#{pages}">#{pages}</a>)
            elsif page < pages-10
              %Q(<a href="#pagelist">...</a> <a href="#{uri_pre}#{pages}">#{pages}</a>)
            end
          } ]
          </span>
        </div>
)
pages_div = %Q(
        <div class="pages" id="all_pages">
        <a name="pagelist"></a>
          #{
            plen = pages.to_s.length
            (1..pages).map{|i|
              if i == page
                %Q(<span class="current">#{i.to_s.rjust(plen,"0")}</span>)
              else
                %Q(<a href="#{uri_pre}#{i}">#{i.to_s.rjust(plen,"0")}</a>)
              end
            }.compact.join(" ")
          }
        </div>
)

current_page = %Q(
        <div id="current_page">
          #{
            unless page == pages
              %Q(<a href="#{uri_pre}#{(page % pages) + 1}">)
            end
          }<img style="border:1px solid black;" alt="Image of page #{page}" src="#{page_pre}#{page}">#{
            unless page == pages
              "</a>"
            end
          }
        </div>
)

page_thumbs = %Q(
        <div id="page_thumbs">
        </div>
)

thumb_size = 128
thumb_dims = dims(metadata, thumb_size)
thumb_text = %Q(
          #{
            pgu = "page.cgi?item=#{URI.escape(filename)}&size=#{thumb_size}&page="
            sp = [1, page-2].max
#             (sp..[sp+4, pages].min)
            (1..pages).map{|i|
              if i == page
                %Q(<span id="current_page_thumb"><img src="#{pgu}#{i}"><br>#{i}</span>)
              else
                %Q(<a href="#{uri_pre}#{i}"><img src="#{pgu}#{i}"><br>#{i}</a>)
              end
            }.compact.join("<br>")
          }
)

text = %Q(
  <div id="page_text" style="display:none;">
    #{
      CGI.escapeHTML(page_text).gsub("\n", "<br>")
    }
  </div>
)

citations = citation_links.empty? ? "" : %Q(
  <div id="citations">
    <ul><li>
      #{citation_links.join("</li><li>")}
    </li></ul>
  </div>
)


item_metadata = %Q(
  <div id="metadata">
    <form>
      <div class="item_metadata">
        <p><a href="#{URI.escape(filename)}">download</a>
        (#{
          if filename.split(".").last.downcase != 'pdf'
            %Q(<a href="convert.cgi?type=pdf&item=#{URI.escape(filename)}">PDF</a> | )
          end
        }<a href="convert.cgi?type=mp3&item=#{URI.escape(filename)}">MP3</a>
        | <a href="convert.cgi?type=txt&item=#{URI.escape(filename)}">text</a>)
        </p>
      </div>
      <h3>Filename</h3>
      <p>
        #{CGI.escapeHTML( File.basename(filename) )}
      </p>
      <h3>Title</h3>
      <p>
        #{CGI.escapeHTML( metadata['Doc.Title'].to_s )}
      </p>
      <h3>Author(s)</h3>
      <p>
        #{CGI.escapeHTML( metadata['Doc.Author'].to_s )}
      </p>
      <h3>Date</h3>
      <p>
        #{CGI.escapeHTML( metadata['Doc.Modified'].to_s )}
      </p>
      #{"<h3>Words</h3><p>#{metadata['Doc.WordCount']}</p>" if metadata['Doc.WordCount']}
      <h3>Pages</h3>
      <p>
        #{metadata['Doc.PageCount']}
      </p>
      <h3>Page size</h3>
      <p>
        #{metadata['Image.Width'].to_f.round}x#{metadata['Image.Height'].to_f.round}#{metadata['Image.DimensionUnit']}
        #{metadata['Doc.PageSizeName'] ? "(#{metadata['Doc.PageSizeName']})" : ""}
      </p>
      <h3>Description</h3>
      <p>
        #{CGI.escapeHTML(metadata['Doc.Description'] || "")}
      </p>
      <h3>References</h3>
      <p>
        #{citations}
      </p>
    </form>
  </div>
)

stylesheet = %Q(
  <style type="text/css">
    a {
      color: #248;
    }
    #page_list a {
      padding-left: 1px;
      padding-right: 1px;
    }
    a:visited {
      color: #422;
    }
    a:hover {
      color: #48a;
    }
    #top_navigation span {
      padding-left:1px;
      padding-right: 1px;
    }
    #page_thumbs {
      text-align: center;
      width: 160px;
      left: 1px;
      top: 0px;
      height: 100%;
      position: absolute;
      overflow: auto;
    }
    #page_thumbs img {
      margin-top: 4px;
    }
    #current_page_thumb img {
      border:8px solid #48a;
    }
    #current_page_thumb {
      color: #48a;
    }
    #metadata {
      width: 256px;
      float: left;
      margin-left: 8px;
      padding-right: 8px;
      padding-top: 4px;
    }
    .item_metadata {
      font-size: 14px;
    }
    .item_metadata a {
      color: black;
    }
    #metadata p {
      font-size: 14px;
      margin-left: 8px;
      margin-top: 2px;
      min-height: 1.5em;
      float: left;
    }
    #metadata div {
      clear:both;
    }
    #metadata .item_metadata p {
      margin-left: 0px;
    }
    #metadata h3 {
      float: left;
      clear: both;
      margin: 0px;
      font-size: 14px;
      margin-top: 1px;
      font-family: Helvetica, Sans-serif;
    }
    #current_page {
      float: left;
      padding-top: 8px;
      margin-bottom: 16px;
    }
    .current {
      color: white;
      background-color: #48a;
    }
    #citations ul {
      padding-left: 20px;
    }
    #citations li {
      list-style: circle;
      font-size: 11px;
      margin-bottom: 4px;
    }
    .comment {
      font-size: 11px;
      margin-left: 8px;
      margin-bottom: 4px;
    }
  </style>
)
script = %Q(
  <script type="text/javascript">
    var ap = document.getElementById('all_pages')
    var tn = document.getElementById('page_list')
    ap.style.borderTop = '1px dotted black'
    ap.style.marginTop = '4px'
    ap.style.marginBottom = '4px'
    ap.style.paddingTop = '4px'
    ap.parentNode.removeChild(ap)
    ap.style.display = 'none'
    links = document.getElementsByTagName('a')
    for (var i=0; i<links.length; i++) {
      var a = links[i]
      if (a.getAttribute('href') == '#pagelist') {
        a.onclick = function(ev) {
          ap.style.display = (ap.style.display == 'none') ? 'block' : 'none'
          return false
        }
      }
    }
    var pt = document.getElementById('page_text')
    var link = document.createElement('a')
    link.innerHTML = 'Toggle page text'
    link.href = '#'
    link.onclick = function(ev) {
      pt.style.display = (pt.style.display == 'none') ? 'block' : 'none'
      return false
    }
    pt.style.borderTop = '1px dotted black'
    pt.style.marginTop = '4px'
    pt.style.paddingTop = '4px'
    tn.appendChild(link)
    tn.appendChild(ap)
    var thumbs = document.getElementById('page_thumbs')
    thumbs.innerHTML = #{thumb_text.dump}
    var ct = document.getElementById('current_page_thumb')
    if (ct && ct.previousSibling && ct.previousSibling.previousSibling && ct.previousSibling.previousSibling.previousSibling)
      thumbs.scrollTop = ct.previousSibling.previousSibling.previousSibling.offsetTop
    var c = document.getElementById('content')
    var s = c.style
    s.position = 'absolute'
    s.paddingLeft = '4px'
    s.left = '161px'
    s.top = '0px'
    s.right = '0px'
    s.height = '100%'
    s.overflow = 'auto'
  </script>
)

content = cgi.html{
  cgi.head{
    cgi.title{ (metadata['Doc.Title'] || File.basename(filename)) + " - page #{page}" } +
    stylesheet
  } +
  cgi.body{
    cgi.div("id"=>'content'){
      short_pages_div +
      text +
      current_page +
      item_metadata +
      pages_div
    } +
    page_thumbs +
    script
  }
}
head = cgi.header(
  "type" => "text/html",
  "length" => content.size,
  "status" => "OK",
  "expires" => Time.now + (86400 * 365),
  "Last-modified" => File.mtime(filename).httpdate
)
cgi.print(head)
cgi.print(content)
times << ['done', Time.now.to_f]

print_profile(times) if use_print_profile


