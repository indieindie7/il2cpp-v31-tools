// Dump decompiled C. args: <out.c> <listfile>; list lines "0x<addr> <name>".
//@category LongDark
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import java.io.*;
import java.nio.file.*;

public class DumpList extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        PrintWriter w = new PrintWriter(new FileWriter(a[0]));
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        int ok = 0, bad = 0;
        for (String line : Files.readAllLines(Paths.get(a[1]))) {
            String[] t = line.trim().split(" ");
            if (t.length < 2) continue;
            Address addr = toAddr(Long.decode(t[0]));
            Function f = getFunctionAt(addr);
            if (f == null) { w.println("// no function for " + line); bad++; continue; }
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            w.println("// ==== " + t[1] + " @ " + addr + " body=" + f.getBody().getNumAddresses());
            if (r.decompileCompleted()) { w.println(r.getDecompiledFunction().getC()); ok++; }
            else { w.println("// failed: " + r.getErrorMessage()); bad++; }
        }
        di.dispose();
        w.close();
        println("DumpList: ok " + ok + " bad " + bad);
    }
}
