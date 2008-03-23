module WReader
extend self

  class << self
    attr_accessor :database_dir, :document_dir, :database_engine,
                  :use_print_profile, :temp_dir
  end
  self.document_dir = "pdfs"

  self.database_engine = WReader::SQLite3
  self.database_dir = "database"
  self.temp_dir = "temp"

  self.use_print_profile = true

  def get_database(*args)
    database_engine.new(*args)
  end

end