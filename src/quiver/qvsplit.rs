use clap::Parser;
use std::process;

mod quiver;
use quiver::{Quiver, QuiverError};

/// Split a Quiver (.qv) file into multiple smaller Quiver files,
/// each containing a specified number of tags.
///
/// Usage:
///     qvsplit mydesigns.qv 100
///     → produces: split_000.qv, split_001.qv, ...
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Quiver file to split
    file: String,

    /// Number of tags per split file
    ntags: usize,

    /// Prefix for the output files (default: "split")
    #[arg(long, default_value = "split")]
    prefix: String,

    /// Directory to save the split files (default: current directory)
    #[arg(long, default_value = ".")]
    output_dir: String,
}

fn main() {
    let args = Args::parse();

    if args.ntags == 0 {
        eprintln!("❌ NTAGS must be a positive integer.");
        process::exit(1);
    }

    println!("📂 Reading: {}", args.file);
    println!("🔪 Splitting into chunks of {} tags...", args.ntags);

    match Quiver::new(&args.file, "r") {
        Ok(q) => {
            if let Err(e) = q.split(args.ntags, &args.output_dir, &args.prefix) {
                eprintln!("❌ Error during split: {:?}", e);
                process::exit(1);
            }
        }
        Err(e) => {
            eprintln!("❌ Failed to open Quiver file: {:?}", e);
            process::exit(1);
        }
    }

    println!(
        "✅ Files written to {} with prefix '{}'",
        args.output_dir, args.prefix
    );
}
