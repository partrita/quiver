use clap::Parser;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Write};
use std::process;

mod quiver;
use quiver::Quiver;

/// Rename the tags in a Quiver file using new tags from stdin or command-line arguments.
///
/// Usage examples:
///     qvls my.qv | sed 's/$/_new/' | qvrename my.qv > renamed.qv
///     qvrename my.qv tag1_new tag2_new ... > renamed.qv
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Quiver file to rename tags in
    quiver_file: String,

    /// New tags (can be empty if piped via stdin)
    new_tags: Vec<String>,
}

fn main() {
    let args = Args::parse();

    // Gather new tags from CLI and possibly from stdin (piped)
    let mut tag_buffers: Vec<String> = args.new_tags.clone();

    // If stdin is piped, read tags from stdin
    if !atty::is(atty::Stream::Stdin) {
        let mut stdin_data = String::new();
        if let Err(e) = io::stdin().read_to_string(&mut stdin_data) {
            eprintln!("❌ Failed to read from stdin: {}", e);
            process::exit(1);
        }
        for line in stdin_data.lines() {
            tag_buffers.extend(line.split_whitespace().map(|s| s.to_string()));
        }
    }

    // Filter out empty entries
    let tags: Vec<String> = tag_buffers.into_iter().filter(|t| !t.trim().is_empty()).collect();

    // Read present tags from the Quiver file
    let qv = match Quiver::new(&args.quiver_file, "r") {
        Ok(q) => q,
        Err(e) => {
            eprintln!("❌ Failed to open Quiver file: {:?}", e);
            process::exit(1);
        }
    };
    let present_tags = qv.get_tags();

    if present_tags.len() != tags.len() {
        eprintln!(
            "❌ Number of tags in file ({}) does not match number of tags provided ({})",
            present_tags.len(),
            tags.len()
        );
        process::exit(1);
    }

    let mut tag_idx = 0;
    let file = match File::open(&args.quiver_file) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("❌ Failed to open file: {}", e);
            process::exit(1);
        }
    };
    let mut reader = BufReader::new(file);
    let stdout = io::stdout();
    let mut handle = stdout.lock();

    let mut buffer = String::new();
    while reader.read_line(&mut buffer).unwrap_or(0) > 0 {
        let mut line = buffer.clone();
        buffer.clear();

        if line.starts_with("QV_TAG") {
            // Replace tag
            line = format!("QV_TAG {}\n", tags[tag_idx]);

            // Read next line (could be QV_SCORE or structure)
            let mut next_line = String::new();
            if reader.read_line(&mut next_line).unwrap_or(0) == 0 {
                // End of file after QV_TAG, just print
                handle.write_all(line.as_bytes()).unwrap();
                break;
            }
            if next_line.starts_with("QV_TAG") {
                eprintln!(
                    "❌ Error: Found two QV_TAG lines in a row. This is not supported. Line: {}",
                    next_line.trim_end()
                );
                process::exit(1);
            }
            if next_line.starts_with("QV_SCORE") {
                let mut parts: Vec<&str> = next_line.split_whitespace().collect();
                if parts.len() > 1 {
                    parts[1] = &tags[tag_idx];
                }
                next_line = format!("{}\n", parts.join(" "));
            }
            line.push_str(&next_line);
            tag_idx += 1;
        }
        handle.write_all(line.as_bytes()).unwrap();
    }
}
