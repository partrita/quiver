use clap::Parser;
use std::collections::HashSet;
use std::io::{self, Read, Write};
use std::process;

mod quiver;
use quiver::{Quiver, QuiverError};

/// Slice a specific set of tags from a Quiver file into another Quiver file.
///
/// Usage:
///     qvslice big.qv tag1 tag2 ... > sliced.qv
///     echo "tag1 tag2" | qvslice big.qv > sliced.qv
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Quiver file to slice from
    quiver_file: String,

    /// Tags to extract (can be empty if piped via stdin)
    tags: Vec<String>,
}

fn main() {
    let args = Args::parse();

    // Collect tags from CLI and possibly from stdin (piped)
    let mut tag_list: Vec<String> = args.tags.clone();

    // If no tags provided as arguments and stdin is piped, read from stdin
    if tag_list.is_empty() && !atty::is(atty::Stream::Stdin) {
        let mut stdin_data = String::new();
        if let Err(e) = io::stdin().read_to_string(&mut stdin_data) {
            eprintln!("❌ Failed to read from stdin: {}", e);
            process::exit(1);
        }
        tag_list.extend(stdin_data.split_whitespace().map(|s| s.to_string()));
    }

    // Clean and validate tag list
    tag_list = tag_list
        .into_iter()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();

    if tag_list.is_empty() {
        eprintln!("❌ No tags provided. Provide tags as arguments or via stdin.");
        process::exit(1);
    }

    let qv = match Quiver::new(&args.quiver_file, "r") {
        Ok(q) => q,
        Err(e) => {
            eprintln!("❌ Failed to open Quiver file: {:?}", e);
            process::exit(1);
        }
    };

    let (qv_lines, found_tags) = match qv.get_struct_list(&tag_list) {
        Ok(res) => res,
        Err(e) => {
            eprintln!("❌ Failed to extract tags: {:?}", e);
            process::exit(1);
        }
    };

    // Warn about missing tags
    let found_set: HashSet<_> = found_tags.iter().collect();
    for tag in &tag_list {
        if !found_set.contains(tag) {
            eprintln!("⚠️  Tag not found in Quiver file: {}", tag);
        }
    }

    // Output sliced content to stdout
    let stdout = io::stdout();
    let mut handle = stdout.lock();
    if let Err(e) = handle.write_all(qv_lines.as_bytes()) {
        eprintln!("❌ Failed to write output: {}", e);
        process::exit(1);
    }
}
