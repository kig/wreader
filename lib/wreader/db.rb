require 'sqlite3'

module WReader

  class SQLite3
    attr_reader :filename, :db

    def initialize(filename="reader.db")
      @filename = filename
      @db = get_database
    end

    def execute(*a)
      db.execute(*a)
    end

    def get_first_row(*a)
      db.get_first_row(*a)
    end

    def get_database
      if File.exist?(filename)
        db = ::SQLite3::Database.new(filename)
      else
        db = ::SQLite3::Database.new(filename)
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

  end

end