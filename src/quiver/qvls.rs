use clap::Parser;
use std::process;

mod quiver;
use quiver::Quiver;

/// List all tags in the given Quiver file.
///
/// Usage:
///     qvls <quiver_file>
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Quiver file to list tags from
    quiver_file: String,
}

fn main() {
    let args = Args::parse();

    let qv = match Quiver::new(&args.quiver_file, "r") {
        Ok(q) => q,
        Err(e) => {
            eprintln!("❌ Failed to open Quiver file: {:?}", e);
            process::exit(1);
        }
    };

    for tag in qv.get_tags() {
        println!("{}", tag);
    }
}
