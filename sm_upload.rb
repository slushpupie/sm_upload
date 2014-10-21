#! /usr/bin/env ruby

require "oauth"
require "ruby-smugmug"
require "json"
require "yaml"
require "find"
require "sqlite3"
require "date"
require "getoptlong"

$known_types = [".jpg", ".jpeg", ".gif", ".png"]

def get_db
	db = SQLite3::Database.new(".sm_cache.db")
	#db = SQLite3::Database.new(":memory:")
	db.execute <<-SQL
	  create table if not exists images (
	  	id varchar[30],
	  	key varchar[256],
	  	filename varchar[256],
	  	album_id int);
	SQL
	db.execute <<-SQL
	  create table if not exists albums (
	  	id varchar[30],
	  	key varchar[256],
	  	name varchar[50],
	  	category_id int,
	  	subcategory_id int,
	  	last_changed datetime);
	SQL
	db.execute <<-SQL
		create table if not exists categories (
			id varchar[30],
			name varchar[50]);
	SQL
	db.execute <<-SQL
		create table if not exists subcategories (
			id varchar[30],
			category_id varchar[30],
			name varchar[50]);
	SQL
	return db;
end


def get_creds

	api_key, oauth_secret, token, secret = YAML.load_file(".sm_upload")

	if token == nil || secret == nil
		@consumer=OAuth::Consumer.new api_key, 
		                              oauth_secret, 
		                              {
		                              		:site=>"https://api.smugmug.com",
		                              		:request_token_path => "/services/oauth/getRequestToken.mg",
		                              		:access_token_path => "/services/oauth/getAccessToken.mg",
		                              		:authorize_path => "/services/oauth/authorize.mg"
		                              }

		@request_token = @consumer.get_request_token                              

		puts "Visit the following URL, log in if you need to, and authorize the app"
		puts @request_token.authorize_url
		puts "When you've authorized that token, enter the verifier code you are assigned (if any):"
		verifier = gets.strip                                                                    

		@access_token=@request_token.get_access_token(:oauth_verifier => verifier)         

		token = @access_token.token
		secret = @access_token.secret

		File.write(".sm_upload", [api_key, oauth_secret, token, secret].to_yaml)
	end

	return [api_key, oauth_secret, token, secret]
end


def get_album(album)
	parts = album.split('/')
	name = nil
	cat = nil
	subcat = nil

	case parts.length
		when 1
			name = parts[0]
			cat = 0
			subcat = 0
		when 2
			cat = get_cat(parts[0])
			name = parts[1]
			subcat = 0
		when 3
			cat = get_cat(parts[0])
			subcat = get_subcat(cat,parts[1])
			name = parts[2]
		else
			# unsupported
			print "Unsupported directory structure (#{album})\n"
			return nil,nil
	end

	rows = $db.execute("SELECT id,key FROM albums WHERE name = ? AND category_id = ? AND subcategory_id = ?",name,cat,subcat)
	if rows.length == 0
		if $do_albums
			print "Creating new album #{album}\n"
			a = $client.albums.create(:Title=>name,:Category=>cat,:SubCategory=>subcat)
			$db.execute("INSERT INTO albums (id,key,name,category_id,subcategory_id,last_changed) VALUES (?,?,?,?,?,datetime('now'))",a["id"], a["Key"],a["Name"],cat,subcat)
			return a["id"],a["Key"]
		else
			print "#{album}\n"
			return [-1,-1]
		end
	elsif rows.length == 1
		return rows[0][0],rows[0][1]
	end

	print "Unknown problem: Multiple albums with the same name (#{album}\n"
	return nil,nil

end

def get_cat(category)
	rows = $db.execute("SELECT id FROM categories WHERE name = ?", category)
	if rows.length == 0
		if $do_albums
			print "Creating new Category #{category}\n"
			c = $client.categories.create(:Name=>category)
			$db.execute("INSERT INTO categories (id,name VALUES (?,?)" ,c["id"],c["Name"])
			return c["id"]
		else
			print "#{category}\n"
			return -1
		end
	elsif rows.length == 1
		return rows[0][0]
	end

	print "Unknown problem: Multiple categories with the same name (#{category})\n"

	return nil

end

def get_subcat(cat_id, subcategory)
	rows = $db.execute("SELECT id FROM subcategories WHERE category_id = ? AND name = ?",cat_id,subcategory)
	if rows.length == 0
		if $do_albums
			print "Creating new subcategory #{subcategory}\n"
			s = $client.subcategories.create(:Name=>subcategory, :CategoryID=>cat_id)
			$db.execute("INSERT INTO subcategories (id,category_id,name) VALUES (?,?,?)",s["id"], s["Category"]["id"], s["Name"])
			return s["id"]
		else
			row = $db.execute("SELECT name FROM categories WHERE id = ?", cat_id)
			print "#{row[0][0]}/#{subcategory}\n"
			return -1
		end
	elsif rows.length == 1
		return rows[0][0]
	end

	print "Unknown problem: Multiple subcategories with the same name (#{subcategory})\n"
	return nil

end


def image_exist?(album_id, album_key, file)
	rows = $db.execute("SELECT * FROM images WHERE filename = ? AND album_id = ?", file, album_id)
	if rows.length == 0
		return false
	elsif rows.length == 1
		return true
	end

	print "Unknown problem: Multiple images with the same name (#{file})\n"
	return true
end

def upload_image(album_id, file)

	if $do_uploads
		image = $client.upload_media(:file => File.new(file), :AlbumID => album_id)
		#image = {"id" => -1, "Key" => "deadbeef", "FileName" => file}
	
		if image==nil || image["id"] == nil
			print "  Upload failed.\n"
		else
			# update cache
			rows = $db.execute("INSERT INTO images (id,key,filename,album_id) VALUES (?,?,?,?)",image["id"],image["Key"],image["FileName"],album_id)
		end

	end

end


def update_cache(force_all=false)

	$db.transaction

	debug_print("Updating categories")
	categories = $client.categories.get
	$db.execute("DELETE FROM categories")
	categories.each { |cat|
		$db.execute("INSERT INTO categories (id,name) VALUES (?,?)",cat["id"],cat["Name"])
	}

	debug_print("Updating subcategories")
	subcategories = $client.subcategories.getAll
	$db.execute("DELETE FROM subcategories")
	subcategories.each { |subcat|
		$db.execute("INSERT INTO subcategories (id,name,category_id) VALUES (?,?,?)",subcat["id"],subcat["Name"],subcat["Category"]["id"])
	}

	if(force_all)
		lastUpdated = 0
	else
		row = $db.execute("SELECT last_changed FROM albums ORDER BY last_changed DESC LIMIT 1");
	    if row.length == 1
	        lastUpdated = DateTime.parse(row[0][0]).strftime("%s")
	    end
	end


	debug_print("Updating albums")
	albums = $client.albums.get(:LastUpdated=>lastUpdated)

	albums.each { |album|


		id = album["id"]
		key = album["Key"]
		name = album["Title"]
		cat = 0
		subcat = 0
		if album["Category"] != nil
			cat = album["Category"]["id"]
		end
		if album["SubCategory"] != nil
			subcat = album["SubCategory"]["id"]
		end

		sm_info = $client.albums.getInfo(:AlbumID=>id,:AlbumKey=>key)
		db_info = $db.execute("SELECT last_changed FROM albums WHERE id = ?",id)
		update_required = false

		if db_info.length == 0
			# Not in database, lets update
			$db.execute("INSERT INTO albums (id,key,name,category_id,subcategory_id,last_changed) VALUES (?,?,?,?,?,'1970-01-01')",id, key,name,cat,subcat)
			update_required = true
		elsif db_info.length == 1
			db_last_changed = DateTime.parse(db_info[0][0])
			sm_last_changed = DateTime.parse(sm_info["LastUpdated"])
			if sm_last_changed.strftime("%s") > db_last_changed.strftime("%s")
				update_required = true
			end
		else
			print "Unknown problem: Multiple albums with the same name (#{album})\n"
			return
		end

		if force_all || update_required
			print "Updating #{name} cache"
			$db.execute("DELETE FROM images WHERE album_id = ?",id)
			
			data = $client.images.get(:AlbumID=>id,:AlbumKey=>key,:Heavy=>true)
			images = data["Images"]
			images.each { |image|
				print "."
				$db.execute("INSERT INTO images (id,key,filename,album_id) VALUES (?,?,?,?)",
								image["id"],
								image["Key"],
								image["FileName"],
								id)
			}
			print "\n"
			$db.execute("UPDATE albums SET last_changed = ? WHERE id = ?",sm_info["LastUpdated"],id);
		else
			print "Cache for #{name} is current\n"
		end

	}

	$db.commit
end



def debug
	$categories.each{ |category| 
		print "c:#{category["Name"]} (#{category["id"]})\n"
		$subcats.each { |subcat|
			next if not subcat["Category"]["id"] == category["id"]
			print "  s:#{subcat["Name"]} (#{subcat["id"]})\n"
			$albums.each { |album|
				next if not album["Category"]["id"] == category["id"] && album["SubCategory"] != nil && album["SubCategory"]["id"] == subcat["id"]
				print "    a:#{album["Title"]} (#{album["id"]})\n"
			}
		}
		$albums.each { |album|
			next if not album["Category"]["id"] == category["id"] && album["SubCategory"] == nil
			print "  a:#{album["Title"]} (#{album["id"]})\n"
		}
	}

	$albums.each { |album|
		next if not album["Category"]["id"] == nil && album["SubCategory"] == nil
		print "a:#{album["Title"]} (#{album["id"]})\n"
	}
end

def dump_image_cache
	print $image_cache
end

def debug_print(*args)
	print *args
	print "\n"
end

def show_help
	print <<-EOF
			sm_upload [OPTIONS]

			-h, --help:         Show help
			-u, --update-cache: Update the local image cache first
			-n, --no-upload:    Don't upload images
			-a, --no-albums:    Don't create albums/categories/subcategories
	EOF
end

api_key, oauth_secret, token, secret = get_creds
$client = SmugMug::Client.new( :api_key => api_key, :oauth_secret=>oauth_secret, :user => {:token => token, :secret=>secret})
#$albums = $client.albums.get
#$categories = $client.categories.get
#$subcats = $client.subcategories.getAll
#$image_cache = {}
$db = get_db
$do_uploads = true;
$do_albums  = true;

opts = GetoptLong.new(
	[ '--help',         '-h', GetoptLong::NO_ARGUMENT],
	[ '--update-cache', '-u', GetoptLong::NO_ARGUMENT],
	[ '--no-upload',    '-n', GetoptLong::NO_ARGUMENT],
	[ '--no-albums',    '-a', GetoptLong::NO_ARGUMENT]
	)

force_cache_update=false
opts.each do |opt,arg|
	case opt
	when '--help'
		show_help
		exit
	when '--update-cache'
		print "Updating cache. Please be patient\n"
		force_cache_update=true
	when '--no-upload'
		$do_uploads = false
	when '--no-albums'
		$do_albums = false
	end
end

update_cache(force_cache_update)

Find.find('Categories') do |file|
	skip = false
        skip_reason = ""
	next if not FileTest.file?(file)
	if not $known_types.include?(File.extname(file).downcase)
		skip = true
                skip_reason = "?"
	end
	if File.fnmatch(".*",file) #skip dot files
		skip = true
                skip_reason = "H"
	end


	album = File.dirname(file.slice(11,file.length))
	image = File.basename(file)

	# Skip hidden dirs
	hidden = false
	album.split("/").each{ |dir| 
		if dir.start_with?(".")
			hidden = true
			break
		end
	}
	if hidden
		hidden = false
		skip = true
                skip_reason = "H"
	end


	if skip
		print "##{skip_reason}#{file.slice(11,file.length)}\n"
		next
	end

	album_id, album_key = get_album(album)

	if not album_id
		print "Could not create album #{album}\n"
		exit 1
	end

	
	if not image_exist?(album_id,album_key,image)
		print "#{album}/#{image}\n"
		upload_image(album_id,file)
        else
		print "#E#{album}/#{image}\n"
                
	end


end
