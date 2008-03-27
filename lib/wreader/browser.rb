require 'wreader/db'

module WReader


  class Browser
    attr_reader :db
    
    def initialize(database=WReader.database)
      @db = database
    end

    def items
      fnts = @db.execute(%Q(
        SELECT filename, title
        FROM items
        ORDER BY title, filename
      ))
      fnts.map{|fn| Item.new(*fn) }
    end
    
  end

  
  class Item
    attr_reader :path, :title

    def initialize(path, title)
      @path = path
      @title = title || File.basename(path)
    end
    
  end
  
  
end
