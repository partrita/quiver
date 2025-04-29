use clap::Parser;
use std::fs::{self, File};
use std::io::Write;
use std::path::Path;
use std::process;

mod quiver;
use quiver::{Quiver, QuiverError};

/// Extract all PDB files from a Quiver file.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to the Quiver file
    quiver_file: String,
}

fn main() {
    let args = Args::parse();

    if let Err(e) = extract_pdbs(&args.quiver_file) {
        eprintln!("❌ Error: {:?}", e);
        process::exit(1);
    }
}

fn extract_pdbs(quiver_file: &str) -> Result<(), QuiverError> {
    let qv = Quiver::new(quiver_file, "r")?;

    for tag in qv.get_tags() {
        let outfn = format!("{}.pdb", tag);

        if Path::new(&outfn).exists() {
            println!("⚠️  File {} already exists, skipping", outfn);
            continue;
        }

        let lines = qv.get_pdblines(&tag)?;
        let mut file = File::create(&outfn)?;
        for line in lines {
            file.write_all(line.as_bytes())?;
            if !line.ends_with('\n') {
                file.write_all(b"\n")?;
            }
        }

        println!("✅ Extracted {}", outfn);
    }

    println!(
        "\n🎉 Successfully extracted {} PDB files from {}",
        qv.size(),
        quiver_file
    );

    Ok(())
}
