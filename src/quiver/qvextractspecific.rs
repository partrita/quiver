use clap::{Parser};
use std::collections::HashSet;
use std::fs::{self, File};
use std::io::{self, BufRead, Write};
use std::path::{Path, PathBuf};
use std::process;

mod quiver;
use quiver::{Quiver, QuiverError};

// This is a command-line tool to extract specific PDB files from a Quiver file.

// Usage:
//     qvextractspecific.py [OPTIONS] <quiver_file> [tag1 tag2 ...]
//     cat tags.txt | qvextractspecific.py [OPTIONS] <quiver_file>
/// Extract specific PDB files from a Quiver file.
///
/// Tags can be passed as command-line arguments or via stdin (piped).
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to the Quiver file
    quiver_file: String,

    /// Tags to extract (can be empty if piped via stdin)
    tags: Vec<String>,

    /// Directory to save extracted PDB files
    #[arg(short, long, default_value = ".", value_name = "DIR")]
    output_dir: String,
}

fn main() {
    let args = Args::parse();

    if let Err(e) = extract_selected_pdbs(&args) {
        eprintln!("❌ Error: {:?}", e);
        process::exit(1);
    }
}

fn extract_selected_pdbs(args: &Args) -> Result<(), QuiverError> {
    // Collect tags from CLI and possibly from stdin (piped)
    let mut tag_buffers: Vec<String> = args.tags.clone();

    // Check if stdin is piped (not a tty)
    if !atty::is(atty::Stream::Stdin) {
        let stdin = io::stdin();
        for line in stdin.lock().lines() {
            let line = line?;
            tag_buffers.extend(line.split_whitespace().map(|s| s.to_string()));
        }
    }

    // Clean and deduplicate tags
    let mut unique_tags: Vec<String> = tag_buffers
        .into_iter()
        .filter(|s| !s.trim().is_empty())
        .collect::<HashSet<_>>()
        .into_iter()
        .collect();
    unique_tags.sort();

    if unique_tags.is_empty() {
        eprintln!("❗ No tags provided.");
        process::exit(1);
    }

    // Ensure output directory exists
    fs::create_dir_all(&args.output_dir)?;

    let qv = Quiver::new(&args.quiver_file, "r")?;
    let mut extracted_count = 0;

    for tag in &unique_tags {
        let outfn = Path::new(&args.output_dir).join(format!("{}.pdb", tag));
        if outfn.exists() {
            println!("⚠️  File {} already exists, skipping", outfn.display());
            continue;
        }

        match qv.get_pdblines(tag) {
            Ok(lines) => {
                let mut file = File::create(&outfn)?;
                for line in lines {
                    file.write_all(line.as_bytes())?;
                    if !line.ends_with('\n') {
                        file.write_all(b"\n")?;
                    }
                }
                println!("✅ Extracted {}", outfn.display());
                extracted_count += 1;
            }
            Err(QuiverError::TagNotFound(_)) => {
                println!("❌ Could not find tag {} in Quiver file, skipping", tag);
            }
            Err(e) => return Err(e),
        }
    }

    println!(
        "\n🎉 Successfully extracted {} PDB file(s) from {} to {}",
        extracted_count,
        args.quiver_file,
        args.output_dir
    );
    Ok(())
}
